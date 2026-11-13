#!/usr/bin/env python3
"""Render page 1 of each PDF in docs/ to docs/thumbs/<sha1(filename)[:12]>.webp.

Requires: pip install pymupdf pillow
Usage:    python3 tools/generate_thumbnails.py [--docs docs] [--width 360] [--force]
Existing thumbnails newer than their PDF are skipped.
"""
import argparse, hashlib, io
from pathlib import Path
import fitz
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--docs", default="docs")
ap.add_argument("--width", type=int, default=360)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
docs = Path(a.docs); out = docs / "thumbs"; out.mkdir(exist_ok=True)
made = skipped = failed = 0
for p in sorted(docs.glob("*.pdf")):
    dest = out / (hashlib.sha1(p.name.encode()).hexdigest()[:12] + ".webp")
    if dest.exists() and not a.force and dest.stat().st_mtime >= p.stat().st_mtime:
        skipped += 1; continue
    try:
        with fitz.open(p) as d:
            page = d[0]
            zoom = a.width / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            img.save(dest, "WEBP", quality=70, method=6)
        made += 1
    except Exception as e:
        failed += 1; print(f"FAILED {p.name}: {e}")
print(f"thumbnails: {made} made, {skipped} up to date, {failed} failed")
