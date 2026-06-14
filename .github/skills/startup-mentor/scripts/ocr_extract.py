#!/usr/bin/env python3
"""
OCR Text & Table Extraction from Images

Extracts text, tables, and structured data from images.
Supports multiple OCR backends:
  1. pytesseract (Tesseract OCR) - primary
  2. easyocr - fallback

Usage:
  python .github/skills/startup-mentor/scripts/ocr_extract.py --image path/to/image.png
  python .github/skills/startup-mentor/scripts/ocr_extract.py --image path/to/image.png --output .tmp/extracted.json
  python .github/skills/startup-mentor/scripts/ocr_extract.py --image path/to/image.png --format csv
  python .github/skills/startup-mentor/scripts/ocr_extract.py --image path/to/image.png --format table
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _detect_backend():
    """Return the best available OCR backend."""
    try:
        import pytesseract  # noqa: F401
        return "pytesseract"
    except ImportError:
        pass
    try:
        import easyocr  # noqa: F401
        return "easyocr"
    except ImportError:
        pass
    return None


# ---------------------------------------------------------------------------
# OCR engines
# ---------------------------------------------------------------------------

def ocr_with_pytesseract(image_path):
    """Extract text using pytesseract."""
    import pytesseract
    from PIL import Image
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    # Also try to get structured data (TSV) for table parsing
    tsv_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DATAFRAME)
    return text, tsv_data


def ocr_with_easyocr(image_path):
    """Extract text using easyocr."""
    import easyocr
    reader = easyocr.Reader(["en"], gpu=False)
    results = reader.readtext(image_path, detail=1)
    # Sort by vertical position (top to bottom), then horizontal (left to right)
    results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
    text = "\n".join([r[1] for r in results])
    return text, results


# ---------------------------------------------------------------------------
# Table parsing helpers
# ---------------------------------------------------------------------------

def parse_table_from_text(raw_text):
    """
    Heuristically parse a table from raw OCR text.
    Looks for lines with consistent delimiters (tabs, multiple spaces, pipes).
    Returns a list of rows (each row is a list of cell strings).
    """
    lines = [l for l in raw_text.strip().splitlines() if l.strip()]
    rows = []
    for line in lines:
        # Try tab-separated first
        if "\t" in line:
            cells = [c.strip() for c in line.split("\t") if c.strip()]
        # Try pipe-separated
        elif "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
        # Fall back to 2+ spaces as delimiter
        else:
            cells = [c.strip() for c in re.split(r"  +", line) if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def rows_to_dicts(rows):
    """Convert rows (first row = header) to list of dicts."""
    if len(rows) < 2:
        return rows
    headers = rows[0]
    result = []
    for row in rows[1:]:
        d = {}
        for i, h in enumerate(headers):
            d[h] = row[i] if i < len(row) else ""
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

def extract(image_path, backend=None):
    """
    Run OCR on an image and return structured results.

    Returns dict with keys:
      - raw_text: full extracted text
      - table_rows: list of lists (parsed table)
      - table_dicts: list of dicts (if header row detected)
      - backend: which engine was used
    """
    if backend is None:
        backend = _detect_backend()
    if backend is None:
        print("ERROR: No OCR backend installed.", file=sys.stderr)
        print("Install one of:", file=sys.stderr)
        print("  pip install pytesseract Pillow   (+ Tesseract binary)", file=sys.stderr)
        print("  pip install easyocr", file=sys.stderr)
        sys.exit(1)

    tsv_data = None
    if backend == "pytesseract":
        raw_text, tsv_data = ocr_with_pytesseract(image_path)
    elif backend == "easyocr":
        raw_text, _ = ocr_with_easyocr(image_path)
    else:
        raise ValueError(f"Unknown backend: {backend}")

    table_rows = parse_table_from_text(raw_text)
    table_dicts = rows_to_dicts(table_rows) if len(table_rows) >= 2 else []

    return {
        "raw_text": raw_text,
        "table_rows": table_rows,
        "table_dicts": table_dicts,
        "backend": backend,
        "source": str(image_path),
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_output(result, fmt="json"):
    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)
    elif fmt == "text":
        return result["raw_text"]
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        for row in result["table_rows"]:
            writer.writerow(row)
        return buf.getvalue()
    elif fmt == "table":
        lines = []
        for row in result["table_rows"]:
            lines.append(" | ".join(str(c) for c in row))
        return "\n".join(lines)
    else:
        return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract text & tables from images via OCR")
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument("--output", help="Save output to this file path")
    parser.add_argument("--format", default="json", choices=["json", "text", "csv", "table"],
                        help="Output format (default: json)")
    parser.add_argument("--backend", choices=["pytesseract", "easyocr"],
                        help="Force a specific OCR backend")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = extract(str(image_path), backend=args.backend)
    output = format_output(result, args.format)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Saved to {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
