#!/usr/bin/env python3
"""Add a consistent author tab to every public book page."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
START = "<!-- author-tab:start -->"
END = "<!-- author-tab:end -->"

LABELS = {
    "en": "About the Author: Faramarz Kowsari",
    "tr": "Yazar Hakkında: Faramarz Kowsari",
    "de": "Über den Autor: Faramarz Kowsari",
    "es": "Sobre el autor: Faramarz Kowsari",
    "fr": "À propos de l’auteur : Faramarz Kowsari",
    "fa": "درباره نویسنده: Faramarz Kowsari",
}


def page_language(text):
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, re.I)
    if not match:
        return "en"
    return match.group(1).lower().split("-")[0]


def remove_existing(text):
    return re.sub(
        re.escape(START) + r'.*?' + re.escape(END) + r'\s*',
        "",
        text,
        flags=re.S,
    )


def author_block(lang):
    label = LABELS.get(lang, LABELS["en"])
    return (
        f"\n{START}\n"
        '<nav class="book-tabs" aria-label="Book navigation">\n'
        f'  <a class="book-tab author-tab" href="../author/">{label}</a>\n'
        '</nav>\n'
        f"{END}\n"
    )


def insert_after_breadcrumbs(text, block):
    breadcrumbs = re.search(
        r'<nav\s+class=["\']breadcrumbs["\'][^>]*>.*?</nav>',
        text,
        flags=re.S | re.I,
    )
    if breadcrumbs:
        return text[:breadcrumbs.end()] + block + text[breadcrumbs.end():]

    main = re.search(r'<main\b[^>]*>', text, re.I)
    if main:
        return text[:main.end()] + block + text[main.end():]
    return text


def main():
    updated = 0
    for path in sorted(BOOKS.glob("*/index.html")):
        if path.parent.name == "author":
            continue
        text = path.read_text(encoding="utf-8")
        clean = remove_existing(text)
        rendered = insert_after_breadcrumbs(clean, author_block(page_language(clean)))
        if rendered != text:
            path.write_text(rendered, encoding="utf-8")
            updated += 1
    print(f"Author tab added or refreshed on {updated} book pages.")


if __name__ == "__main__":
    main()
