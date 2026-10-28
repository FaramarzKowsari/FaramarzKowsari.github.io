#!/usr/bin/env python3
"""Ensure book cover images link directly to the matching Google Books page."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
CATALOG = BOOKS / "catalog.json"
INDEX = BOOKS / "index.html"

BOOK_TOP_RE = re.compile(r'<section class="book-top"[^>]*>[\s\S]*?</section>', re.I)
LINKED_COVER_RE = re.compile(
    r'(<section class="book-top"[^>]*>\s*)'
    r'<a\b[^>]*>\s*(<img\b[^>]*>)\s*</a>',
    re.I,
)
DIRECT_COVER_RE = re.compile(
    r'(<section class="book-top"[^>]*>\s*)(<img\b[^>]*>)',
    re.I,
)


def esc_attr(value: str) -> str:
    return html.escape(str(value), quote=True)


def link_cover_on_landing(page: Path, title: str, google_url: str) -> bool:
    text = page.read_text(encoding="utf-8")
    match = BOOK_TOP_RE.search(text)
    if not match:
        return False

    section = match.group(0)
    if re.search(
        rf'<a\b[^>]*href=["\']{re.escape(google_url)}["\'][^>]*>\s*<img\b',
        section,
        re.I,
    ):
        return False

    def replacement(match: re.Match[str]) -> str:
        return (
            match.group(1)
            + f'<a class="book-cover-link" href="{esc_attr(google_url)}" '
              f'target="_blank" rel="noopener noreferrer" '
              f'aria-label="View {esc_attr(title)} on Google Books">'
            + match.group(2)
            + '</a>'
        )

    if LINKED_COVER_RE.search(section):
        new_section = LINKED_COVER_RE.sub(replacement, section, count=1)
    elif DIRECT_COVER_RE.search(section):
        new_section = DIRECT_COVER_RE.sub(replacement, section, count=1)
    else:
        return False

    updated = text[: match.start()] + new_section + text[match.end() :]
    page.write_text(updated, encoding="utf-8")
    return True


def link_main_index_cover(text: str, slug: str, google_url: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf'<a href=["\']\./{re.escape(slug)}/["\']([^>]*)>'
        rf'(<img class=["\']cover["\'])',
        re.I,
    )
    def replacement(match: re.Match[str]) -> str:
        return (
            f'<a href="{esc_attr(google_url)}" target="_blank" '
            f'rel="noopener noreferrer"{match.group(1)}>'
            + match.group(2)
        )

    updated, count = pattern.subn(replacement, text, count=1)
    return updated, bool(count)


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    books = catalog.get("books", [])

    canonical_changes = 0
    localized_changes = 0
    index_changes = 0
    index_text = INDEX.read_text(encoding="utf-8")

    for book in books:
        slug = book.get("slug")
        google_url = book.get("google_books_url")
        title = book.get("title") or slug or "Book"
        if not slug or not google_url:
            continue

        book_dir = BOOKS / slug
        canonical = book_dir / "index.html"

        if canonical.exists() and link_cover_on_landing(canonical, title, google_url):
            canonical_changes += 1

        if book_dir.exists():
            for page in book_dir.rglob("index.html"):
                if page == canonical:
                    continue
                if link_cover_on_landing(page, title, google_url):
                    localized_changes += 1

        index_text, changed = link_main_index_cover(index_text, slug, google_url)
        if changed:
            index_changes += 1

    INDEX.write_text(index_text, encoding="utf-8")
    print(
        "Google Books cover links: "
        f"{canonical_changes} canonical pages, "
        f"{localized_changes} localized pages, "
        f"{index_changes} main-index cards updated."
    )


if __name__ == "__main__":
    main()
