#!/usr/bin/env python3
"""Enforce the books library's external-image-only policy on public entry pages.

No locally hosted image, social-preview banner, or image file is created.
Book covers remain served by Google Books; book-specific Pinterest imagery is
served from Pinterest. Clickable covers should point to their Google Books ID.

Keep --root-only and --books-only for existing GitHub workflows.
"""
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
BANNER = re.compile(
    r"<!-- library-social-preview:start -->.*?<!-- library-social-preview:end -->\\s*",
    flags=re.I | re.S,
)
STYLE = re.compile(
    r'<style id="library-social-preview-style">.*?</style>\\s*',
    flags=re.I | re.S,
)
META = re.compile(
    r'<meta\\b[^>]*(?:Social%20Preview\\.jpg)[^>]*>\\s*',
    flags=re.I,
)
ALT = re.compile(
    r'<meta\\s+(?:property="og:image:alt"|name="twitter:image:alt")'
    r'\\s+content="Faramarz Kowsari Official Website and Multilingual Books Library[^"]*"[^>]*>\\s*',
    flags=re.I,
)
FAVICON = re.compile(
    r'<link\\s+rel="icon"\\s+href="favicon\\.svg"[^>]*>\\s*',
    flags=re.I,
)

def clean_file(relative_path: str) -> bool:
    path = ROOT / relative_path
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8")
    updated = BANNER.sub("", original)
    updated = STYLE.sub("", updated)
    updated = META.sub("", updated)
    updated = ALT.sub("", updated)
    if relative_path == "index.html":
        updated = FAVICON.sub("", updated)
    # If no Open Graph image survives, do not advertise a large-image card.
    if not re.search(r'<meta\\s+property="og:image"\\s+content="', updated, flags=re.I):
        updated = updated.replace('content="summary_large_image"', 'content="summary"')
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True

def main() -> None:
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--root-only", action="store_true")
    selection.add_argument("--books-only", action="store_true")
    args = parser.parse_args()
    paths = []
    if not args.books_only:
        paths.append("index.html")
    if not args.root_only:
        paths.extend(["books/index.html", "books/topics/index.html", "books/all-books/index.html"])
    modified = [p for p in paths if clean_file(p)]
    print("External-image-only cleanup: " + (", ".join(modified) if modified else "already compliant"))

if __name__ == "__main__":
    main()
