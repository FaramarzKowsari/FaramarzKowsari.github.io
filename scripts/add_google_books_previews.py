#!/usr/bin/env python3
"""Add a direct Google Books reader-preview callout to every public book page."""

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA_FILES = [BOOKS / "books.json", BOOKS / "completed.json", BOOKS / "source-reviewed-extra.json"]

START = "<!-- google-books-preview:start -->"
END = "<!-- google-books-preview:end -->"

COPY = {
    "en": (
        "Free Google Books Preview",
        "Read a free sample of this book on Google Books before you buy.",
        "Read the free preview on Google Books",
    ),
    "tr": (
        "Ücretsiz Google Books Önizlemesi",
        "Satın almadan önce kitabın ücretsiz örnek sayfalarını Google Books'ta okuyun.",
        "Google Books'ta ücretsiz önizlemeyi oku",
    ),
    "es": (
        "Vista previa gratuita en Google Books",
        "Lee gratis una muestra de este libro en Google Books antes de comprarlo.",
        "Leer la vista previa gratis en Google Books",
    ),
    "fr": (
        "Aperçu gratuit sur Google Books",
        "Lisez gratuitement un extrait de ce livre sur Google Books avant de l’acheter.",
        "Lire l’aperçu gratuit sur Google Books",
    ),
    "de": (
        "Kostenlose Google-Books-Vorschau",
        "Lesen Sie vor dem Kauf eine kostenlose Vorschau dieses Buches bei Google Books.",
        "Kostenlose Vorschau bei Google Books lesen",
    ),
    "fa": (
        "پیش‌نمایش رایگان در Google Books",
        "پیش از خرید، نمونهٔ رایگان این کتاب را در Google Books بخوانید.",
        "مطالعهٔ پیش‌نمایش رایگان در Google Books",
    ),
}

PREVIEW_ICON = """<div class=\"preview-icon\" aria-hidden=\"true\"><svg viewBox=\"0 0 48 48\" focusable=\"false\"><rect x=\"3\" y=\"3\" width=\"42\" height=\"42\" rx=\"12\" fill=\"currentColor\" opacity=\".08\"/><path d=\"M10.5 14.5c4.8-1.8 9-1.3 13.5 1.4v20.8c-4.5-2.7-8.7-3.2-13.5-1.4V14.5Zm27 0c-4.8-1.8-9-1.3-13.5 1.4v20.8c4.5-2.7 8.7-3.2 13.5-1.4V14.5Z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linejoin=\"round\"/><circle cx=\"32\" cy=\"26.5\" r=\"5.2\" fill=\"white\" stroke=\"currentColor\" stroke-width=\"2\"/><path d=\"m35.8 30.3 4.2 4.2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.3\" stroke-linecap=\"round\"/></svg></div>"""


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def collect_ids():
    """Collect slug -> Google Books ID from the catalog and enrichment files."""
    mapping = {}
    for path in DATA_FILES:
        data = load_json(path, {} if path.name != "books.json" else [])
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = []
            for slug, value in data.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("slug", slug)
                    rows.append(row)
        else:
            rows = []
        for row in rows:
            slug = row.get("slug")
            gid = row.get("google_books_id")
            if slug and gid:
                mapping[slug] = str(gid).strip()
    return mapping


def extract_id_from_html(text):
    patterns = (
        r'play\.google\.com/store/books/details\?id=([A-Za-z0-9_-]+)',
        r'play\.google\.com/books/reader\?id=([A-Za-z0-9_-]+)',
        r'books\.google\.[^/"\']+/books\?id=([A-Za-z0-9_-]+)',
        r'frontcover/([A-Za-z0-9_-]+)\?fife=',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def page_language(text):
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, re.I)
    if not match:
        return "en"
    return match.group(1).lower().split("-")[0]


def remove_existing_block(text):
    return re.sub(
        re.escape(START) + r'.*?' + re.escape(END) + r'\s*',
        "",
        text,
        flags=re.S,
    )


def preview_block(gid, lang):
    title, note, label = COPY.get(lang, COPY["en"])
    preview_url = f"https://play.google.com/books/reader?id={gid}&hl=en"
    return (
        f"\n{START}\n"
        f'<section class="section google-books-preview" aria-label="Google Books preview">\n'
        f'  {PREVIEW_ICON}\n'
        f'  <p class="preview-title">{html.escape(title)}</p>\n'
        f'  <p class="preview-note">{html.escape(note)}</p>\n'
        f'  <div class="actions"><a class="action" href="{html.escape(preview_url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(label)}</a></div>\n'
        f"</section>\n"
        f"{END}\n"
    )


def insert_after_book_top(text, block):
    top = re.search(r'<section\s+class=["\']book-top["\'][^>]*>.*?</section>', text, re.S | re.I)
    if top:
        return text[: top.end()] + block + text[top.end() :]
    main = re.search(r'<main\b[^>]*>', text, re.I)
    if main:
        return text[: main.end()] + block + text[main.end() :]
    return text


def main():
    ids = collect_ids()
    updated = 0
    skipped = []

    for path in sorted(BOOKS.glob("*/index.html")):
        slug = path.parent.name
        text = path.read_text(encoding="utf-8")
        clean = remove_existing_block(text)
        gid = ids.get(slug) or extract_id_from_html(clean)
        if not gid:
            skipped.append(slug)
            if clean != text:
                path.write_text(clean, encoding="utf-8")
            continue

        block = preview_block(gid, page_language(clean))
        rendered = insert_after_book_top(clean, block)
        if rendered != text:
            path.write_text(rendered, encoding="utf-8")
            updated += 1

    print(f"Google Books preview links added or refreshed on {updated} book pages.")
    if skipped:
        print(f"Skipped {len(skipped)} page(s) without a detectable Google Books ID: " + ", ".join(skipped))


if __name__ == "__main__":
    main()
