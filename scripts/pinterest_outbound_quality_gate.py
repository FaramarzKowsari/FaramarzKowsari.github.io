#!/usr/bin/env python3
"""Fail the build if any GitHub Books page sends a clickable link to Pinterest.

Pinterest-hosted image bytes (img src on i.pinimg.com) are allowed. User-facing
hyperlinks to pinterest.com or i.pinimg.com are forbidden: Pinterest visuals must
route to the corresponding Google Play Books page instead.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
HREF_RE = re.compile(r'href\s*=\s*(["\'])(.*?)\1', re.I | re.S)

errors = []
checked = 0

for path in sorted(BOOKS.rglob("*.html")):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        continue
    checked += 1

    for match in HREF_RE.finditer(text):
        url = html.unescape(match.group(2)).strip()
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            continue
        if host == "i.pinimg.com" or host == "pinterest.com" or host.endswith(".pinterest.com"):
            errors.append(f"{path.relative_to(ROOT)}: forbidden Pinterest outbound href: {url}")

if errors:
    for item in errors[:120]:
        print("ERROR:", item)
    if len(errors) > 120:
        print(f"ERROR: {len(errors) - 120} additional Pinterest outbound link(s) omitted.")
    print(f"Pinterest outbound quality gate FAILED with {len(errors)} forbidden link(s).")
    sys.exit(1)

print(
    f"Pinterest outbound quality gate PASSED across {checked} HTML page(s): "
    "Pinterest-hosted images may load, but no user click links to Pinterest."
)
