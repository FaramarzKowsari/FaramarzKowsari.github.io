#!/usr/bin/env python3
"""Apply one canonical Faramarz Kowsari Person entity across the books library.

The layer is deliberately split between what readers see and what machines see:
- readers get one compact linked byline on individual book pages;
- JSON-LD on every Book points to the same Person @id;
- the books index mentions the author once, rather than repeating the byline on cards;
- the author profile and root site expose the expanded Person entity;
- one identity JSON file is the durable source of truth for future builds.

Run this after all base and localized book pages have been generated and before the
SEO quality gate.
"""

from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
ENTITY_FILE = BOOKS / "author" / "entity.json"
AUTHOR_PAGE_FILE = BOOKS / "author" / "index.html"
BOOKS_INDEX = BOOKS / "index.html"
ROOT_INDEX = ROOT / "index.html"

HEAD_START = "<!-- author-entity:start -->"
HEAD_END = "<!-- author-entity:end -->"
VISIBLE_START = "<!-- author-visible:start -->"
VISIBLE_END = "<!-- author-visible:end -->"
ALTNAME_START = "<!-- author-alt-name:start -->"
ALTNAME_END = "<!-- author-alt-name:end -->"
LEGACY_TAB_START = "<!-- author-tab:start -->"
LEGACY_TAB_END = "<!-- author-tab:end -->"

SCRIPT_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)

BYLINE_LABELS = {
    "en": "By",
    "tr": "Yazar:",
    "de": "Von",
    "es": "Por",
    "fr": "Par",
    "pt": "Por",
    "pt-br": "Por",
    "ru": "Автор:",
    "fa": "نویسنده:",
    "ar": "المؤلف:",
    "id": "Oleh",
    "vi": "Tác giả:",
    "th": "ผู้เขียน:",
    "bn": "লেখক:",
    "ro": "De",
}


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def type_has(node: dict, wanted: str) -> bool:
    value = node.get("@type")
    if isinstance(value, list):
        return wanted in value
    return value == wanted


def page_language(text: str) -> str:
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, re.I)
    if not match:
        return "en"
    return match.group(1).lower()


def remove_marked(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\s*", "", text, flags=re.S)


def replace_jsonld(text: str, mutator) -> tuple[str, int]:
    changed = 0

    def repl(match: re.Match) -> str:
        nonlocal changed
        raw = match.group(2).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)
        did_change = mutator(payload)
        if not did_change:
            return match.group(0)
        changed += 1
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return f"{match.group(1)}{encoded}{match.group(3)}"

    return SCRIPT_RE.sub(repl, text), changed


def walk(node, visitor) -> bool:
    changed = False
    if isinstance(node, dict):
        changed = visitor(node) or changed
        for value in list(node.values()):
            if isinstance(value, (dict, list)):
                changed = walk(value, visitor) or changed
    elif isinstance(node, list):
        for value in node:
            if isinstance(value, (dict, list)):
                changed = walk(value, visitor) or changed
    return changed


def make_author_ref(entity: dict) -> dict:
    return {
        "@type": "Person",
        "@id": entity["person_id"],
        "name": entity["name"],
        "alternateName": entity.get("alternate_name", []),
        "url": entity["author_page"],
        "image": entity["image"],
    }


def patch_book_jsonld(text: str, entity: dict) -> tuple[str, int]:
    ref = make_author_ref(entity)

    def mutate(payload) -> bool:
        def visit(node: dict) -> bool:
            changed = False
            if type_has(node, "Book"):
                if node.get("author") != ref:
                    node["author"] = dict(ref)
                    changed = True
                publisher = node.get("publisher")
                if isinstance(publisher, dict) and clean(publisher.get("name")).casefold() == entity["name"].casefold():
                    desired = dict(ref)
                    if publisher != desired:
                        node["publisher"] = desired
                        changed = True
            return changed
        return walk(payload, visit)

    return replace_jsonld(text, mutate)


def expanded_person(entity: dict) -> dict:
    person = {
        "@type": "Person",
        "@id": entity["person_id"],
        "name": entity["name"],
        "alternateName": entity.get("alternate_name", []),
        "url": entity["website"],
        "mainEntityOfPage": entity["author_page"],
        "image": entity["image"],
        "description": entity["short_description"],
        "jobTitle": entity.get("job_titles", []),
        "homeLocation": {"@type": "Place", "name": entity.get("location", "Istanbul")},
        "knowsAbout": entity.get("knows_about", []),
        "identifier": [
            {
                "@type": "PropertyValue",
                "propertyID": "ORCID",
                "value": entity["orcid"],
                "url": entity["profiles"]["orcid"],
            }
        ],
        "sameAs": entity.get("same_as", []),
    }
    return person


def patch_person_jsonld(text: str, entity: dict, patch_collection: bool = False) -> tuple[str, int]:
    desired = expanded_person(entity)
    person_id = entity["person_id"]
    collection_id = "https://faramarzkowsari.github.io/books/#collection"

    def mutate(payload) -> bool:
        def visit(node: dict) -> bool:
            changed = False
            if type_has(node, "Person") and node.get("@id") == person_id:
                old_context = node.get("@context")
                node.clear()
                node.update(desired)
                if old_context and "@context" not in node:
                    node["@context"] = old_context
                changed = True
            if patch_collection and type_has(node, "CollectionPage") and node.get("@id") == collection_id:
                ref = {"@id": person_id}
                if node.get("author") != ref:
                    node["author"] = ref
                    changed = True
            return changed
        return walk(payload, visit)

    return replace_jsonld(text, mutate)


def ensure_head_identity(text: str, entity: dict) -> str:
    text = remove_marked(text, HEAD_START, HEAD_END)
    text = re.sub(r'<meta\b(?=[^>]*\bname=["\']author["\'])[^>]*>\s*', "", text, flags=re.I)
    text = re.sub(r'<link\b(?=[^>]*\brel=["\']author["\'])[^>]*>\s*', "", text, flags=re.I)
    block = (
        f"\n{HEAD_START}\n"
        f'<meta name="author" content="{html.escape(entity["name"], quote=True)}">\n'
        f'<link rel="author" href="{html.escape(entity["author_page"], quote=True)}" title="{html.escape(entity["name"], quote=True)} author profile">\n'
        f"{HEAD_END}\n"
    )
    if "</head>" in text:
        return text.replace("</head>", block + "</head>", 1)
    return text


def ensure_visible_byline(text: str, entity: dict) -> str:
    text = remove_marked(text, LEGACY_TAB_START, LEGACY_TAB_END)
    text = remove_marked(text, VISIBLE_START, VISIBLE_END)
    lang = page_language(text)
    label = BYLINE_LABELS.get(lang, BYLINE_LABELS.get(lang.split("-", 1)[0], "By"))
    display_name = entity["name"]
    if lang.startswith("fa"):
        display_name += " (فرامرز کوثری)"
    block = (
        f"\n{VISIBLE_START}\n"
        f'<p class="meta author-byline">{html.escape(label)} '
        f'<a rel="author" href="{html.escape(entity["author_page"], quote=True)}">{html.escape(display_name)}</a></p>\n'
        f"{VISIBLE_END}\n"
    )
    h1 = re.search(r"<h1\b[^>]*>.*?</h1>", text, flags=re.I | re.S)
    if not h1:
        return text
    return text[: h1.end()] + block + text[h1.end() :]


def patch_book_page(path: pathlib.Path, entity: dict) -> bool:
    original = path.read_text(encoding="utf-8")
    text, _ = patch_book_jsonld(original, entity)
    text = ensure_head_identity(text, entity)
    text = ensure_visible_byline(text, entity)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def patch_author_page(entity: dict) -> bool:
    if not AUTHOR_PAGE_FILE.exists():
        raise SystemExit("books/author/index.html is missing")
    original = AUTHOR_PAGE_FILE.read_text(encoding="utf-8")
    text, _ = patch_person_jsonld(original, entity)
    text = ensure_head_identity(text, entity)

    image = html.escape(entity["image"], quote=True)
    text = re.sub(r'(<meta\s+property=["\']og:image["\']\s+content=["\'])[^"\']+(["\'])', rf'\g<1>{image}\2', text, flags=re.I)
    text = re.sub(r'(<meta\s+name=["\']twitter:image["\']\s+content=["\'])[^"\']+(["\'])', rf'\g<1>{image}\2', text, flags=re.I)
    text = re.sub(
        r'(<img\b[^>]*class=["\'][^"\']*\bauthor-photo\b[^"\']*["\'][^>]*\bsrc=["\'])[^"\']+(["\'])',
        rf'\g<1>{image}\2',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'(<img\b[^>]*\bsrc=["\'])[^"\']+(["\'][^>]*class=["\'][^"\']*\bauthor-photo\b[^"\']*["\'])',
        rf'\g<1>{image}\2',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'(<img\b[^>]*\bauthor-photo\b[^>]*\balt=["\'])[^"\']*(["\'])',
        r'\g<1>Portrait of Faramarz Kowsari\2',
        text,
        flags=re.I,
    )

    text = remove_marked(text, ALTNAME_START, ALTNAME_END)
    alt_block = (
        f"\n{ALTNAME_START}\n"
        '<p class="meta author-alt-name" lang="fa" dir="rtl">فرامرز کوثری</p>\n'
        f"{ALTNAME_END}\n"
    )
    h1 = re.search(r"<h1\b[^>]*>\s*Faramarz Kowsari\s*</h1>", text, flags=re.I)
    if h1:
        text = text[: h1.end()] + alt_block + text[h1.end() :]

    if text != original:
        AUTHOR_PAGE_FILE.write_text(text, encoding="utf-8")
        return True
    return False


def patch_root_and_books_indexes(entity: dict) -> int:
    updated = 0
    if ROOT_INDEX.exists():
        original = ROOT_INDEX.read_text(encoding="utf-8")
        text, _ = patch_person_jsonld(original, entity, patch_collection=True)
        text = ensure_head_identity(text, entity)
        if text != original:
            ROOT_INDEX.write_text(text, encoding="utf-8")
            updated += 1
    if BOOKS_INDEX.exists():
        original = BOOKS_INDEX.read_text(encoding="utf-8")
        text, _ = patch_person_jsonld(original, entity, patch_collection=True)
        text = ensure_head_identity(text, entity)
        if text != original:
            BOOKS_INDEX.write_text(text, encoding="utf-8")
            updated += 1
    return updated


def iter_public_book_pages(books: list[dict]):
    seen: set[pathlib.Path] = set()
    for book in books:
        if book.get("status", "active") != "active":
            continue
        slug = clean(book.get("slug"))
        if not slug:
            continue
        root = BOOKS / slug
        base = root / "index.html"
        if base.exists() and base not in seen:
            seen.add(base)
            yield base
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            localized = child / "index.html"
            if localized.exists() and localized not in seen:
                seen.add(localized)
                yield localized


def validate_entity(entity: dict) -> None:
    required = [
        "person_id", "name", "alternate_name", "website", "author_page", "image",
        "bio", "short_description", "orcid", "profiles", "same_as",
    ]
    missing = [key for key in required if not entity.get(key)]
    if missing:
        raise SystemExit(f"Author entity is missing required field(s): {', '.join(missing)}")
    if entity["person_id"] != "https://faramarzkowsari.github.io/#person":
        raise SystemExit("Author entity person_id must remain the canonical site-wide #person ID")
    if entity["name"] != "Faramarz Kowsari":
        raise SystemExit("Author entity canonical name changed unexpectedly")
    if "فرامرز کوثری" not in entity.get("alternate_name", []):
        raise SystemExit("Author entity must preserve the Persian alternate name")


def main() -> None:
    entity = load_json(ENTITY_FILE, {})
    validate_entity(entity)
    books = load_json(DATA, [])
    if not isinstance(books, list):
        raise SystemExit("books/books.json must contain a JSON array")

    updated_books = 0
    checked_books = 0
    for path in iter_public_book_pages(books):
        checked_books += 1
        if patch_book_page(path, entity):
            updated_books += 1

    author_updated = patch_author_page(entity)
    index_updates = patch_root_and_books_indexes(entity)

    print(
        "Author Entity Layer applied: "
        f"{checked_books} book/localized pages checked, {updated_books} updated; "
        f"author page updated={author_updated}; index pages updated={index_updates}."
    )


if __name__ == "__main__":
    main()
