#!/usr/bin/env python3
"""Normalize ALT text for Google Books-hosted book-cover images.

Each cover is described in the language of the page with a strictly descriptive
pattern equivalent to:
    Book cover of <Book Title> by Faramarz Kowsari

Supported site locales: English, Russian, Turkish, German, Spanish, French and
Brazilian Portuguese. Unknown locales fall back to English.

The localized wording is also applied to Open Graph and Twitter image ALT
metadata when those social images are served by Google Books.

This post-processing step intentionally describes the image itself only. It does
not add marketplace or availability language such as "available on Google Books"
to ALT text. The Google Books relationship remains expressed elsewhere through
image URLs, purchase/preview links and structured metadata.

This is a text-only step. It never downloads, copies, caches, proxies, resizes or
stores any external image in the repository.
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
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.I)
TAG_RE = re.compile(r"<[^>]+>")

AUTHOR = "Faramarz Kowsari"


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def set_attr(tag: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pat = re.compile(rf'''(\b{re.escape(name)}\s*=\s*)(["']).*?\2''', re.I | re.S)
    if pat.search(tag):
        return pat.sub(lambda m: f'{m.group(1)}"{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", fragment))).strip()


def page_title(text: str) -> str:
    m = H1_RE.search(text)
    return plain_text(m.group(1)) if m else ""


def page_locale(text: str, path: pathlib.Path) -> str:
    """Return the site's normalized locale for this HTML page."""
    m = HTML_LANG_RE.search(text)
    if m:
        raw = m.group(1).strip().lower().replace("_", "-")
        if raw.startswith("pt"):
            return "pt-br"
        primary = raw.split("-", 1)[0]
        if primary in {"en", "ru", "tr", "de", "es", "fr"}:
            return primary

    parts = {part.lower() for part in path.parts}
    if "pt-br" in parts:
        return "pt-br"
    for locale in ("ru", "tr", "de", "es", "fr"):
        if locale in parts:
            return locale
    return "en"


def is_google_books_image(url: str) -> bool:
    value = html.unescape(url or "").lower()
    return (
        "books.google.com/books/content" in value
        or "books.googleusercontent.com" in value
    )


def title_from_existing_alt(current: str) -> str:
    """Recover a book title from common ALT formats already used by the site."""
    value = html.unescape((current or "").strip())
    if not value:
        return ""

    patterns = [
        r"^Book cover of\s+(.+?)\s+by Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
        r"^(.+?)\s+book cover(?:\s+by Faramarz Kowsari)?(?:,?\s+available on Google Books)?$",
        r"^Обложка книги [«\"](.+?)[»\"] автора Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
        r"^(.+?)\s*[—-]\s*Faramarz Kowsari kitap kapağı(?:\s*[—-]\s*Google Books)?$",
        r"^Buchcover von [„\"](.+?)[“\"] von Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
        r"^Portada del libro [«\"](.+?)[»\"] de Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
        r"^Couverture du livre [«\"](.+?)[»\"] de Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
        r"^Capa do livro [“\"](.+?)[”\"],? de Faramarz Kowsari(?:\s*[—-]\s*Google Books)?$",
    ]
    for pattern in patterns:
        m = re.match(pattern, value, re.I)
        if m:
            return m.group(1).strip()

    # Conservative cleanup for older generated forms.
    cleaned = re.sub(r"\s*[—-]\s*Google Books\s*$", "", value, flags=re.I)
    cleaned = re.sub(r",?\s*available on Google Books\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^Book cover of\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+by Faramarz Kowsari\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*[—-]\s*Faramarz Kowsari\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+book cover\s*$", "", cleaned, flags=re.I)
    return cleaned.strip()


def localized_alt(title: str, locale: str) -> str:
    clean_title = re.sub(r"\s+", " ", (title or "").strip()) or "Book"
    templates = {
        "en": "Book cover of {title} by {author}",
        "ru": "Обложка книги «{title}» автора {author}",
        "tr": "{title} — {author} kitap kapağı",
        "de": "Buchcover von „{title}“ von {author}",
        "es": "Portada del libro «{title}» de {author}",
        "fr": "Couverture du livre «{title}» de {author}",
        "pt-br": "Capa do livro “{title}”, de {author}",
    }
    template = templates.get(locale, templates["en"])
    return template.format(title=clean_title, author=AUTHOR)


def google_image_count(text: str) -> int:
    count = 0
    for m in IMG_RE.finditer(text):
        if is_google_books_image(attrs(m.group(0)).get("src", "")):
            count += 1
    return count


def update_img_tags(text: str, path: pathlib.Path) -> tuple[str, int]:
    count = 0
    locale = page_locale(text, path)
    single_cover = google_image_count(text) == 1
    h1_title = page_title(text) if single_cover else ""

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        data = attrs(tag)
        if not is_google_books_image(data.get("src", "")):
            return tag
        title = h1_title or title_from_existing_alt(data.get("alt", "")) or "Book"
        new_tag = set_attr(tag, "alt", localized_alt(title, locale))
        if new_tag != tag:
            count += 1
        return new_tag

    return IMG_RE.sub(repl, text), count


def update_social_alt(text: str, path: pathlib.Path) -> tuple[str, int]:
    """Keep Open Graph/Twitter image ALT consistent for Google Books covers."""
    social_image_is_google = False
    for m in META_RE.finditer(text):
        data = attrs(m.group(0))
        key = (data.get("property") or data.get("name") or "").lower()
        if key in {"og:image", "twitter:image"} and is_google_books_image(data.get("content", "")):
            social_image_is_google = True
            break
    if not social_image_is_google:
        return text, 0

    locale = page_locale(text, path)
    h1_title = page_title(text)
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        data = attrs(tag)
        key = (data.get("property") or data.get("name") or "").lower()
        if key not in {"og:image:alt", "twitter:image:alt"}:
            return tag
        title = h1_title or title_from_existing_alt(data.get("content", "")) or "Book"
        new_tag = set_attr(tag, "content", localized_alt(title, locale))
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
        out, img_count = update_img_tags(text, path)
        out, social_count = update_social_alt(out, path)
        if out != text:
            path.write_text(out, encoding="utf-8")
            files_changed += 1
            img_alts_changed += img_count
            social_alts_changed += social_count

    print(
        "Localized strict Google Books ALT normalization: "
        f"{files_changed} HTML file(s) changed; "
        f"{img_alts_changed} image ALT attribute(s) updated; "
        f"{social_alts_changed} social image ALT tag(s) updated."
    )


if __name__ == "__main__":
    main()
