#!/usr/bin/env python3
"""Ensure every Google Books-hosted image in the books site has ALT text
containing the exact phrases "Faramarz Kowsari" and "Google Books".

This is a text-only post-processing step. It never downloads, copies, caches,
proxies, resizes or stores any external image in the repository.
"""
from __future__ import annotations

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"

IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
META_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', re.I | re.S)

AUTHOR = "Faramarz Kowsari"
SOURCE = "Google Books"


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def set_attr(tag: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pat = re.compile(rf'''(\b{re.escape(name)}\s*=\s*)(["']).*?\2''', re.I | re.S)
    if pat.search(tag):
        return pat.sub(lambda m: f'{m.group(1)}"{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def is_google_books_image(url: str) -> bool:
    value = html.unescape(url or "").lower()
    return (
        "books.google.com/books/content" in value
        or "books.googleusercontent.com" in value
    )


def enrich_alt(current: str) -> str:
    value = (current or "").strip()
    if not value:
        value = "Book cover"
    if AUTHOR.lower() not in value.lower():
        value += f" — {AUTHOR}"
    if SOURCE.lower() not in value.lower():
        value += f" — {SOURCE}"
    return value


def update_img_tags(text: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        data = attrs(tag)
        if not is_google_books_image(data.get("src", "")):
            return tag
        new_alt = enrich_alt(data.get("alt", ""))
        new_tag = set_attr(tag, "alt", new_alt)
        if new_tag != tag:
            count += 1
        return new_tag

    return IMG_RE.sub(repl, text), count


def update_social_alt(text: str) -> tuple[str, int]:
    """Keep Open Graph/Twitter image alt consistent on pages whose social image
    is also served by Google Books.
    """
    social_image_is_google = False
    for m in META_RE.finditer(text):
        data = attrs(m.group(0))
        key = (data.get("property") or data.get("name") or "").lower()
        if key in {"og:image", "twitter:image"} and is_google_books_image(data.get("content", "")):
            social_image_is_google = True
            break
    if not social_image_is_google:
        return text, 0

    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        data = attrs(tag)
        key = (data.get("property") or data.get("name") or "").lower()
        if key not in {"og:image:alt", "twitter:image:alt"}:
            return tag
        new_value = enrich_alt(data.get("content", ""))
        new_tag = set_attr(tag, "content", new_value)
        if new_tag != tag:
            count += 1
        return new_tag

    return META_RE.sub(repl, text), count


def main() -> None:
    files_changed = 0
    img_alts_changed = 0
    social_alts_changed = 0

    for path in sorted(BOOKS.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        out, img_count = update_img_tags(text)
        out, social_count = update_social_alt(out)
        if out != text:
            path.write_text(out, encoding="utf-8")
            files_changed += 1
            img_alts_changed += img_count
            social_alts_changed += social_count

    print(
        "Google Books ALT enforcement: "
        f"{files_changed} HTML file(s) changed; "
        f"{img_alts_changed} image ALT attribute(s) updated; "
        f"{social_alts_changed} social image ALT tag(s) updated."
    )


if __name__ == "__main__":
    main()
