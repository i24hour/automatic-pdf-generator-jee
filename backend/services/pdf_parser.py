"""
PDF Parser Service — Gemini Vision API powered.

Converts every PDF page to a high-resolution image and sends it to Gemini Vision,
which reads the page like a human and extracts structured JEE Mains questions.

Works for:
  - Text-based PDFs
  - Scanned / image-based PDFs
  - Mixed PDFs with diagrams and figures
"""

import os
import io
import re
import json
import base64
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field

import fitz  # PyMuPDF — used only for page → image conversion
import litellm


# ---------------------------------------------------------------------------
# Data classes (kept compatible with existing router code)
# ---------------------------------------------------------------------------

@dataclass
class ExtractedImage:
    page_number: int
    bbox: Tuple[float, float, float, float]
    image_bytes: bytes
    ext: str = "png"


@dataclass
class ExtractedQuestion:
    question_number: int
    text: str
    options: Dict[str, str] = field(default_factory=dict)
    answer: Optional[str] = None
    answer_value: Optional[str] = None
    q_type: str = "mcq"          # "mcq" | "numerical"
    subject: str = "Physics"
    image_bboxes: List[Tuple] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    page_number: int = 0
    has_diagram: bool = False


@dataclass
class ParseResult:
    title: str = ""
    duration_minutes: int = 180
    exam_type: str = "JEE_MAINS"
    questions: List[ExtractedQuestion] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    answer_key: Dict[int, str] = field(default_factory=dict)
    subjects_found: List[str] = field(default_factory=list)
    pages_total: int = 0


# ---------------------------------------------------------------------------
# Gemini Vision prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are an expert JEE Mains / NEET exam question extractor.
Carefully read the exam page image and extract EVERY question on this page.

RULES:
1. A question starts with its number (e.g. "1.", "Q.1", "1)", "2.").
2. MCQ options are labeled A, B, C, D  (or (A), (B) etc.).
3. Numerical / Integer type questions have NO A-D options.
4. Subject must be ONE of: Physics, Chemistry, Maths, Zoology, Botany.
5. If a section header like "SECTION A — PHYSICS" appears, use that subject for following questions.
6. Include ALL text of the question, including formulas.  Use LaTeX notation for math: $\\frac{1}{2}mv^2$.
7. If the question has a figure/diagram embedded in it, write [DIAGRAM] at that position in the text and set has_diagram to true.
8. If this page is a COVER PAGE, INSTRUCTIONS PAGE, or ANSWER KEY page with no question bodies, return an empty array [].

OUTPUT FORMAT — return ONLY a raw JSON array, no markdown fences, no explanation:
[
  {
    "question_number": 1,
    "text": "Full question text. [DIAGRAM] if a figure appears here.",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "answer": "B",
    "type": "mcq",
    "subject": "Physics",
    "has_diagram": false
  },
  {
    "question_number": 2,
    "text": "An integer-type question text.",
    "options": {},
    "answer": "4",
    "type": "numerical",
    "subject": "Chemistry",
    "has_diagram": false
  }
]

If no questions are found on this page, return exactly: []
"""


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------

class PDFParser:
    """Parse JEE / NEET PDFs using Gemini Vision — works for ALL PDF types."""

    # Model used for vision extraction (override via env var PDF_PARSE_MODEL)
    VISION_MODEL = os.getenv("PDF_PARSE_MODEL", "gemini/gemini-2.5-flash")
    PAGE_DPI = 200          # Higher = better OCR, larger payload
    MAX_PAGES = 60          # Safety limit per upload

    def __init__(self):
        self._setup_api_key()

    def _setup_api_key(self):
        """Ensure GEMINI_API_KEY is set (also accepts GOOGLE_API_KEY)."""
        if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
            print("[PDFParser] Mapped GOOGLE_API_KEY -> GEMINI_API_KEY")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        pdf_path: str,
        title: str = "",
        duration_minutes: int = 180,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ParseResult:
        """
        Main entry point.  Parse any JEE/NEET PDF using Gemini Vision.

        Args:
            pdf_path:          Absolute path to the uploaded PDF.
            title:             Test title (passed through).
            duration_minutes:  Test duration (passed through).
            progress_callback: Optional fn(pages_done, pages_total) called after each page.

        Returns:
            ParseResult with all extracted questions and embedded images.
        """
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), self.MAX_PAGES)

        result = ParseResult(
            title=title,
            duration_minutes=duration_minutes,
            pages_total=total_pages,
        )

        # question_number → ExtractedQuestion  (avoids duplicates from page overlaps)
        seen: Dict[int, ExtractedQuestion] = {}
        all_images: List[ExtractedImage] = []

        print(f"[PDFParser] Starting Vision extraction: {total_pages} pages, model={self.VISION_MODEL}")

        for page_idx in range(total_pages):
            page = doc.load_page(page_idx)
            page_num = page_idx + 1

            # ── Convert page to PNG ──────────────────────────────────
            mat = fitz.Matrix(self.PAGE_DPI / 72, self.PAGE_DPI / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")

            # ── Collect embedded images (for diagram upload later) ──
            page_imgs = self._extract_embedded_images(doc, page, page_num)
            all_images.extend(page_imgs)

            # ── Send page to Gemini Vision ───────────────────────────
            try:
                page_questions = self._extract_from_page_image(img_bytes, page_num)
                new_count = 0
                for q in page_questions:
                    if q.question_number not in seen:
                        seen[q.question_number] = q
                        new_count += 1
                print(f"[PDFParser] Page {page_num}/{total_pages}: {new_count} new questions extracted")
            except Exception as e:
                print(f"[PDFParser] Page {page_num} failed: {e}")

            if progress_callback:
                try:
                    progress_callback(page_idx + 1, total_pages)
                except Exception:
                    pass

        doc.close()

        # Sort by question number
        result.questions = [seen[k] for k in sorted(seen.keys())]
        result.images = all_images

        # Collect unique subjects
        subjects = list({q.subject for q in result.questions
                         if q.subject not in ("Unknown", "")})
        result.subjects_found = subjects or ["Physics", "Chemistry", "Maths"]

        print(f"[PDFParser] Done: {len(result.questions)} questions, "
              f"{len(result.images)} images, subjects={result.subjects_found}")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_embedded_images(
        self, doc: fitz.Document, page: fitz.Page, page_num: int
    ) -> List[ExtractedImage]:
        """Extract raw embedded images from a PDF page for later S3 upload."""
        images = []
        try:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image or not base_image.get("image"):
                    continue
                img_data = base_image["image"]
                ext = base_image.get("ext", "png")

                # Get bounding box on page
                rects = page.get_image_rects(xref)
                bbox: Tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)
                if rects:
                    r = rects[0]
                    bbox = (float(r.x0), float(r.y0), float(r.x1), float(r.y1))

                # Skip tiny images (likely decorative borders / logos)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w < 50 or h < 50:
                    continue

                images.append(ExtractedImage(
                    page_number=page_num,
                    bbox=bbox,
                    image_bytes=img_data,
                    ext=ext if ext else "png",
                ))
        except Exception as e:
            print(f"[PDFParser] Embedded image extraction error (page {page_num}): {e}")
        return images

    def _extract_from_page_image(
        self, img_bytes: bytes, page_num: int
    ) -> List[ExtractedQuestion]:
        """Send a page PNG to Gemini Vision and parse the JSON response."""
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        response = litellm.completion(
            model=self.VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                ],
            }],
            temperature=0.1,
            max_tokens=8192,
        )

        raw = (response.choices[0].message.content or "[]").strip()
        return self._parse_response(raw, page_num)

    def _parse_response(self, raw: str, page_num: int) -> List[ExtractedQuestion]:
        """Parse Gemini's JSON array response into ExtractedQuestion objects."""
        # Strip markdown fences if present
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned.rstrip())
        cleaned = cleaned.strip()

        # Find outermost JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end <= start:
            print(f"[PDFParser] No JSON array in response for page {page_num}: {cleaned[:100]!r}")
            return []

        try:
            data = json.loads(cleaned[start:end])
        except json.JSONDecodeError as e:
            print(f"[PDFParser] JSON parse error page {page_num}: {e} | raw: {cleaned[start:start+200]!r}")
            return []

        if not isinstance(data, list):
            return []

        questions = []
        for item in data:
            q = self._item_to_question(item, page_num)
            if q is not None:
                questions.append(q)
        return questions

    def _item_to_question(
        self, item: Any, page_num: int
    ) -> Optional[ExtractedQuestion]:
        """Convert a raw dict from Gemini's response into an ExtractedQuestion."""
        if not isinstance(item, dict):
            return None

        # question_number is required
        raw_num = item.get("question_number")
        if raw_num is None:
            return None
        try:
            q_num = int(raw_num)
        except (ValueError, TypeError):
            return None

        # type
        raw_type = str(item.get("type", "mcq")).lower()
        q_type = "numerical" if any(kw in raw_type for kw in ("num", "integer", "nat")) else "mcq"

        # subject
        raw_subj = str(item.get("subject", "Physics")).strip()
        valid_subjects = {"Physics", "Chemistry", "Maths", "Zoology", "Botany"}
        subject = raw_subj if raw_subj in valid_subjects else "Physics"

        # options — normalize to uppercase keys A B C D only
        raw_opts = item.get("options", {})
        if isinstance(raw_opts, dict):
            options = {
                k.upper(): str(v).strip()
                for k, v in raw_opts.items()
                if k.upper() in ("A", "B", "C", "D") and str(v).strip()
            }
        else:
            options = {}

        # answer
        raw_ans = item.get("answer")
        answer: Optional[str] = None
        if raw_ans is not None:
            ans_str = str(raw_ans).strip().upper()
            if ans_str in ("A", "B", "C", "D"):
                answer = ans_str
            elif ans_str.replace(".", "").replace("-", "").replace(" ", "").isdigit():
                answer = ans_str  # numerical answer

        # text
        text = str(item.get("text", "")).strip()

        return ExtractedQuestion(
            question_number=q_num,
            text=text,
            options=options,
            answer=answer,
            q_type=q_type,
            subject=subject,
            page_number=page_num,
            has_diagram=bool(item.get("has_diagram", False)),
        )

    # ------------------------------------------------------------------
    # Output serialisation (router uses this)
    # ------------------------------------------------------------------

    def to_json(self, result: ParseResult) -> List[Dict[str, Any]]:
        """Convert ParseResult to JSON-serialisable list for DB storage."""
        return [
            {
                "question_number": q.question_number,
                "text": q.text,
                "options": q.options,
                "answer": q.answer,
                "answer_value": q.answer_value,
                "type": q.q_type,
                "subject": q.subject,
                "image_bboxes": list(q.image_bboxes),
                "image_urls": q.image_urls,
                "page_number": q.page_number,
                "has_diagram": q.has_diagram,
            }
            for q in result.questions
        ]


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
pdf_parser = PDFParser()
