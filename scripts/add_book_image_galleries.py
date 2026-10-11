#!/usr/bin/env python3
"""Add minimal Pinterest-hosted image galleries to selected book pages.

Every gallery image is rendered from Pinterest's CDN but every click is routed
only to that book's Google Play Books purchase page. No gallery image links back
to Pinterest or to the raw Pinterest image URL. The layer is configuration-
driven, idempotent, and safe for future builds.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
CONFIG = BOOKS / "book-image-galleries.json"
START = "<!-- book-image-gallery:start -->"
END = "<!-- book-image-gallery:end -->"

GOOGLE_BOOKS_RE = re.compile(
    r'https://play\.google\.com/store/books/details\?id=[A-Za-z0-9_-]+',
    re.I,
)


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def valid_image_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and host == "i.pinimg.com"
        and parts.path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )


def valid_google_books_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() == "play.google.com"
        and parts.path == "/store/books/details"
        and bool(re.search(r"(?:^|&)id=[A-Za-z0-9_-]+(?:&|$)", parts.query))
    )


def detect_google_books_url(text: str) -> str:
    match = GOOGLE_BOOKS_RE.search(html.unescape(text))
    return match.group(0) if match else ""


def remove_existing(text: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.S)
    return pattern.sub("", text)


def render(slug: str, images: list[str], google_books_url: str) -> str:
    items = []
    book_label = "0DTE Options" if slug == "0dte-options" else slug.replace("-", " ").title()

    for index, url in enumerate(images, start=1):
        label = f"{book_label} visual infographic {index:02d} by Faramarz Kowsari"
        items.append(
            f'''    <a class="book-image-gallery-link" href="{esc(google_books_url)}" target="_blank" rel="noopener noreferrer" aria-label="View or buy {esc(book_label)} on Google Books">
      <img src="{esc(url)}" alt="{esc(label)}" loading="lazy" decoding="async">
    </a>'''
        )

    return f'''{START}
<section class="book-image-gallery" aria-label="{esc(book_label)} visual gallery">
  <style>
    .book-image-gallery{{margin-top:36px;padding-top:8px}}
    .book-image-gallery-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}
    .book-image-gallery-link{{display:block;border-radius:14px;overflow:hidden;background:#f3f4f6;text-decoration:none;box-shadow:0 5px 18px rgba(15,23,42,.08)}}
    .book-image-gallery-link img{{display:block;width:100%;height:100%;aspect-ratio:2/3;object-fit:cover;transition:transform .18s ease}}
    .book-image-gallery-link:hover img{{transform:scale(1.015)}}
    @media(max-width:760px){{.book-image-gallery-grid{{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}}}
  </style>
  <div class="book-image-gallery-grid">
{chr(10).join(items)}
  </div>
</section>
{END}'''


def main() -> None:
    payload = load_json(CONFIG, {})
    if not isinstance(payload, dict):
        raise SystemExit("books/book-image-galleries.json must contain a JSON object")

    errors = []
    updated = 0

    for slug, config in payload.items():
        if not isinstance(config, dict):
            errors.append(f"{slug}: gallery config must be an object")
            continue

        page = BOOKS / slug / "index.html"
        if not page.exists():
            errors.append(f"{slug}: book page does not exist")
            continue

        text = page.read_text(encoding="utf-8")

        raw_images = config.get("images") or []
        images = [str(url).strip() for url in raw_images if str(url).strip()]
        if not images:
            errors.append(f"{slug}: no gallery images configured")
            continue

        bad = [url for url in images if not valid_image_url(url)]
        if bad:
            errors.append(f"{slug}: invalid or non-Pinterest image URL(s): {', '.join(bad)}")
            continue

        if len(set(images)) != len(images):
            errors.append(f"{slug}: duplicate gallery image URL detected")
            continue

        google_books_url = str(config.get("click_url") or "").strip()
        if not google_books_url:
            google_books_url = detect_google_books_url(text)
        if not valid_google_books_url(google_books_url):
            errors.append(f"{slug}: no valid Google Play Books purchase URL found")
            continue

        text = remove_existing(text)
        block = render(slug, images, google_books_url)

        if "</main>" not in text:
            errors.append(f"{slug}: could not find </main> insertion point")
            continue

        # Hard invariant: Pinterest may host the image bytes, but no gallery
        # hyperlink may navigate to Pinterest or the raw CDN asset.
        if 'href="https://i.pinimg.com/' in block or 'href="https://www.pinterest.' in block:
            errors.append(f"{slug}: gallery contains an outbound Pinterest link")
            continue

        gallery_href = f'href="{esc(google_books_url)}"'
        gallery_count = block.count(gallery_href)
        if gallery_count != len(images):
            errors.append(
                f"{slug}: every gallery image must link to Google Books "
                f"(expected {len(images)}, found {gallery_count})"
            )
            continue

        text = text.replace("</main>", block + "\n</main>", 1)

        for url in images:
            if text.count(url) < 1:
                errors.append(f"{slug}: image URL missing from rendered gallery: {url}")

        if text.count(START) != 1 or text.count(END) != 1:
            errors.append(f"{slug}: gallery marker duplication detected")

        page.write_text(text, encoding="utf-8")
        updated += 1

    if errors:
        for item in errors:
            print("ERROR:", item)
        print(f"Book image gallery layer FAILED with {len(errors)} error(s).")
        sys.exit(1)

    print(
        f"Book image gallery layer applied to {updated} book page(s); "
        "all gallery clicks route only to Google Play Books."
    )


if __name__ == "__main__":
    main()
