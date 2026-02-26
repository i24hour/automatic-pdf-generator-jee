"""
extract_jee_archive.py
Extracts text from all JEE Mains 2025/2026 archive PDFs (chapter-wise) from Downloads
and stores them as structured .txt reference files in backend/reference_data/jee_archive/.

Usage: python3 backend/scripts/extract_jee_archive.py
"""

import os
import re
import json
import glob

try:
    import pdfplumber
except ImportError:
    print("Install pdfplumber: pip install pdfplumber")
    exit(1)

# ---- Config ----
PDF_DIR    = os.path.expanduser("~/Downloads/Jee archive 2025")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "reference_data", "jee_archive")
INDEX_FILE = os.path.join(OUTPUT_DIR, "_index.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Normalize chapter name to a clean slug
def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9 ]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name

# Extract topic name from filename like "Ray Optics - JEE Main 2026 (Jan) - MathonGo.pdf"
def extract_topic(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename))[0]
    # Everything before " - JEE"
    match = re.match(r'^(.+?)\s*-\s*JEE', base)
    return match.group(1).strip() if match else base

def extract_pdf_text(pdf_path: str, max_chars: int = 15000) -> str:
    """Extract clean text from a PDF, capped at max_chars."""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                if sum(len(t) for t in text_parts) >= max_chars:
                    break
    except Exception as e:
        print(f"  [ERROR] Could not read {pdf_path}: {e}")
        return ""
    
    full_text = "\n".join(text_parts)
    return full_text[:max_chars]

# ---- Main extraction ----
pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
print(f"Found {len(pdf_files)} PDFs in {PDF_DIR}\n")

index = {}  # topic_name → slug (for lookup at generation time)

for pdf_path in pdf_files:
    topic = extract_topic(pdf_path)
    slug = slugify(topic)
    output_path = os.path.join(OUTPUT_DIR, f"{slug}.txt")

    print(f"Extracting: {topic}")
    text = extract_pdf_text(pdf_path)

    if not text.strip():
        print(f"  [SKIP] No text extracted")
        continue

    # Write metadata header + content
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# JEE Mains 2025/2026 Reference — {topic}\n")
        f.write(f"# Source: MathonGo Chapter Archive\n")
        f.write(f"# Characters: {len(text)}\n\n")
        f.write(text)

    index[topic] = slug
    print(f"  → Saved {len(text):,} chars to {slug}.txt")

# Write index for fast lookup
with open(INDEX_FILE, "w") as f:
    json.dump(index, f, indent=2)

print(f"\n✅ Done! {len(index)} chapters extracted.")
print(f"   Reference files: {OUTPUT_DIR}")
print(f"   Index: {INDEX_FILE}")
