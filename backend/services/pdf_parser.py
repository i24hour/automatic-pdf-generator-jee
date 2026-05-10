"""
PDF Parser Service for PDF-to-Test feature.
Uses PyMuPDF (fitz) to extract text, images, and answer keys from JEE Mains PDFs.
"""

import os
import re
import json
import io
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

import fitz  # PyMuPDF


@dataclass
class ExtractedImage:
    page_number: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    image_bytes: bytes
    ext: str = "png"


@dataclass
class ExtractedQuestion:
    question_number: int
    text: str
    options: Dict[str, str] = field(default_factory=dict)
    answer: Optional[str] = None
    answer_value: Optional[str] = None  # For numerical answers
    q_type: str = "mcq"  # mcq | numerical
    subject: str = "Unknown"
    image_bboxes: List[Tuple[float, float, float, float]] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    page_number: int = 0


@dataclass
class ParseResult:
    title: str = ""
    duration_minutes: int = 180
    exam_type: str = "JEE_MAINS"
    questions: List[ExtractedQuestion] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    answer_key: Dict[int, str] = field(default_factory=dict)
    subjects_found: List[str] = field(default_factory=list)


class PDFParser:
    """Parse JEE Mains PDFs into structured questions with images."""

    # Regex patterns for JEE Mains
    QUESTION_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:Q\.?|Question)?\s*(\d+)\s*[:.\)]\s*(.+?)(?=\n\s*(?:\d+\s*[:.\)]|Q\.?\s*\d+|\Z))',
        re.DOTALL | re.IGNORECASE
    )
    OPTION_PATTERN = re.compile(
        r'\n\s*\(?([A-D])\)?[.\)]\s*(.+?)(?=\n\s*\(?[A-D]\)?[.\)]|\Z)',
        re.DOTALL
    )
    NUMERICAL_HINT = re.compile(
        r'integer\s*type|numerical\s*type|type\s*:\s*numerical|enter\s*\d+',
        re.IGNORECASE
    )
    SECTION_HEADER = re.compile(
        r'(?:Physics|Chemistry|Mathematics|Maths)\s*(?:Section|\(|:)?',
        re.IGNORECASE
    )

    def __init__(self):
        self.image_threshold_px = 150  # Max vertical distance to associate image with question

    def parse(self, pdf_path: str, title: str = "", duration_minutes: int = 180) -> ParseResult:
        """
        Main entry point. Parse a JEE Mains PDF.
        Returns structured questions + raw images.
        """
        doc = fitz.open(pdf_path)
        result = ParseResult(title=title, duration_minutes=duration_minutes)

        all_text_blocks: List[Dict[str, Any]] = []
        all_images: List[ExtractedImage] = []

        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            page_num = page_idx + 1

            # Extract text blocks with bounding boxes
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    text = "\n".join(
                        span["text"] for line in b["lines"] for span in line["spans"]
                    )
                    if text.strip():
                        all_text_blocks.append({
                            "page": page_num,
                            "bbox": b["bbox"],
                            "text": text.strip(),
                        })

            # Extract images
            img_list = page.get_images(full=True)
            for img_index, img in enumerate(img_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]

                # Get image position on page
                # Find the rect where this image appears
                img_rects = self._find_image_rects(page, xref)
                for rect in img_rects:
                    all_images.append(ExtractedImage(
                        page_number=page_num,
                        bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                        image_bytes=image_bytes,
                        ext=ext if ext else "png",
                    ))

        doc.close()

        result.images = all_images

        # Group blocks by page and sort top-to-bottom
        pages_blocks: Dict[int, List[Dict]] = {}
        for b in all_text_blocks:
            pages_blocks.setdefault(b["page"], []).append(b)

        for page_num in pages_blocks:
            pages_blocks[page_num].sort(key=lambda x: x["bbox"][1])  # sort by y0

        # Detect subjects sections
        subjects_found = self._detect_subjects(pages_blocks)
        result.subjects_found = subjects_found

        # Parse questions page by page
        current_subject = "Unknown"
        for page_num in sorted(pages_blocks.keys()):
            blocks = pages_blocks[page_num]
            current_subject = self._parse_page_questions(
                blocks, current_subject, result, page_num
            )

        # Try to find and parse answer key
        result.answer_key = self._extract_answer_key(pages_blocks)

        # Apply answer key to questions
        self._apply_answer_key(result)

        # Associate images with questions by proximity
        self._associate_images(result)

        return result

    def _find_image_rects(self, page: fitz.Page, xref: int) -> List[fitz.Rect]:
        """Find all display rectangles for a given image xref on a page."""
        rects = []
        # Heuristic: look for images in page display list
        for img in page.get_images(full=True):
            if img[0] == xref:
                # We can't get exact bbox easily without parsing the display list,
                # so we approximate by looking for 'xObject' references in raw content
                # A simpler approach: check page.get_text() around image positions
                # For now, use a placeholder approach: if only 1 image per page, assume it spans center
                rects.append(fitz.Rect(50, 100, page.rect.width - 50, page.rect.height - 100))
                break
        if not rects:
            rects.append(fitz.Rect(50, 100, page.rect.width - 50, page.rect.height - 100))
        return rects

    def _detect_subjects(self, pages_blocks: Dict[int, List[Dict]]) -> List[str]:
        """Detect subject section headers across all pages."""
        subjects = []
        for page_num, blocks in pages_blocks.items():
            for b in blocks:
                m = self.SECTION_HEADER.match(b["text"])
                if m:
                    subj = m.group(0).strip().title()
                    if "Math" in subj:
                        subj = "Maths"
                    if subj not in subjects:
                        subjects.append(subj)
        return subjects if subjects else ["Physics", "Chemistry", "Maths"]

    def _parse_page_questions(
        self,
        blocks: List[Dict],
        current_subject: str,
        result: ParseResult,
        page_num: int
    ) -> str:
        """Parse questions from a single page's text blocks."""
        # Concatenate blocks into page text
        page_text = "\n".join(b["text"] for b in blocks)

        # Update current subject if header found
        for b in blocks:
            m = self.SECTION_HEADER.match(b["text"])
            if m:
                current_subject = m.group(0).strip().title()
                if "Math" in current_subject:
                    current_subject = "Maths"

        # Find all question-like blocks using simple heuristics
        q_blocks = self._find_question_blocks(blocks)

        for q_info in q_blocks:
            q_num = q_info["q_num"]
            q_text = q_info["text"]
            q_bbox = q_info["bbox"]

            # Detect if numerical
            is_numerical = bool(self.NUMERICAL_HINT.search(q_text))

            # Extract options from nearby blocks
            options = self._extract_options_for_block(q_info, blocks)

            if not options and not is_numerical:
                # Maybe options are inline in the text
                options = self._extract_inline_options(q_text)

            if not options and not is_numerical:
                # Default to empty — might be a poorly parsed block
                pass

            # Clean question text (remove options from it if embedded)
            clean_text = self._clean_question_text(q_text, options)

            eq = ExtractedQuestion(
                question_number=q_num,
                text=clean_text,
                options=options,
                q_type="numerical" if is_numerical else "mcq",
                subject=current_subject,
                page_number=page_num,
            )
            result.questions.append(eq)

        return current_subject

    def _find_question_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Find blocks that start questions using number patterns."""
        q_blocks = []
        for idx, b in enumerate(blocks):
            text = b["text"]
            # Match start of block: number followed by . ) :
            m = re.match(r'^\s*(\d+)\s*[:.\)]\s*(.*)', text, re.DOTALL)
            if m:
                q_num = int(m.group(1))
                q_text = m.group(2)

                # Accumulate following blocks until next question or big gap
                accumulated = q_text
                for j in range(idx + 1, len(blocks)):
                    next_text = blocks[j]["text"]
                    if re.match(r'^\s*\d+\s*[:.\)]', next_text):
                        break
                    accumulated += "\n" + next_text

                q_blocks.append({
                    "q_num": q_num,
                    "text": accumulated.strip(),
                    "bbox": b["bbox"],
                    "block_index": idx,
                })
        return q_blocks

    def _extract_options_for_block(
        self,
        q_info: Dict,
        blocks: List[Dict]
    ) -> Dict[str, str]:
        """Extract options that appear after a question block."""
        options = {}
        start_idx = q_info["block_index"] + 1

        for j in range(start_idx, min(start_idx + 6, len(blocks))):
            text = blocks[j]["text"]
            opt_matches = list(self.OPTION_PATTERN.finditer("\n" + text))
            for match in opt_matches:
                opt_letter = match.group(1).upper()
                opt_text = match.group(2).strip()
                if opt_letter not in options:
                    options[opt_letter] = opt_text

            # Stop if we hit another question
            if re.match(r'^\s*\d+\s*[:.\)]', text):
                break

        return options

    def _extract_inline_options(self, text: str) -> Dict[str, str]:
        """Try to extract options embedded inside the question text itself."""
        options = {}
        pattern = re.compile(
            r'\(?([A-D])\)?[.\)]\s*([^\n]+?)(?=\s*\(?[A-D]\)?[.\)]|\Z)',
            re.DOTALL
        )
        for match in pattern.finditer(text):
            options[match.group(1).upper()] = match.group(2).strip()
        return options

    def _clean_question_text(self, text: str, options: Dict[str, str]) -> str:
        """Remove option lines from the question body."""
        lines = text.split("\n")
        clean_lines = []
        for line in lines:
            if re.match(r'^\s*\(?[A-D]\)?[.\)]', line):
                continue
            clean_lines.append(line)
        return "\n".join(clean_lines).strip()

    def _extract_answer_key(self, pages_blocks: Dict[int, List[Dict]]) -> Dict[int, str]:
        """Look for answer key section at the end of the document."""
        answer_key = {}
        all_blocks = []
        for page_num in sorted(pages_blocks.keys()):
            all_blocks.extend(pages_blocks[page_num])

        # Heuristic: answer key is usually near the end
        # Look for "Answer Key" header and parse table after it
        in_answer_section = False
        for b in all_blocks:
            text = b["text"]
            if re.search(r'answer\s*key|key\s*answers|solutions', text, re.IGNORECASE):
                in_answer_section = True
                continue

            if in_answer_section:
                # Match "1. A" or "1 A" or "1) B"
                for line in text.split("\n"):
                    m = re.match(r'^\s*(\d+)\s*[:.\)]\s*([A-D]|\d+)', line, re.IGNORECASE)
                    if m:
                        q_num = int(m.group(1))
                        ans = m.group(2).strip().upper()
                        answer_key[q_num] = ans

        return answer_key

    def _apply_answer_key(self, result: ParseResult):
        """Map extracted answers to questions by number."""
        for q in result.questions:
            if q.question_number in result.answer_key:
                ans = result.answer_key[q.question_number]
                q.answer = ans
                if q.q_type == "numerical" or ans.isdigit():
                    q.answer_value = ans
                    q.q_type = "numerical"

    def _associate_images(self, result: ParseResult):
        """Associate extracted images with nearby questions using spatial proximity."""
        for img in result.images:
            img_page = img.page_number
            img_y = img.bbox[1]  # y0 (top)

            # Find questions on the same page
            page_questions = [q for q in result.questions if q.page_number == img_page]
            if not page_questions:
                continue

            # Find nearest question above the image
            best_q = None
            best_dist = float("inf")
            for q in page_questions:
                # Approximate question y position by its question_number order
                # For simplicity, use question_number as proxy for vertical order
                q_idx = page_questions.index(q)
                q_y = q_idx * 200  # rough estimate
                dist = img_y - q_y
                if 0 < dist < best_dist:
                    best_dist = dist
                    best_q = q

            if best_q and best_dist < self.image_threshold_px * 3:  # relax threshold
                best_q.image_bboxes.append(img.bbox)

    def to_json(self, result: ParseResult) -> List[Dict[str, Any]]:
        """Convert parsed result to JSON-serializable list."""
        return [
            {
                "question_number": q.question_number,
                "text": q.text,
                "options": q.options,
                "answer": q.answer,
                "answer_value": q.answer_value,
                "type": q.q_type,
                "subject": q.subject,
                "image_bboxes": q.image_bboxes,
                "image_urls": q.image_urls,
                "page_number": q.page_number,
            }
            for q in result.questions
        ]


# Singleton
pdf_parser = PDFParser()
