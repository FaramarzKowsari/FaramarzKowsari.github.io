#!/usr/bin/env python3
"""
Strengthen image-search signals on every individual book landing page without
hosting, downloading, proxying or caching any book-cover image in this repo.

The existing external cover URL is preserved exactly. It may point to Google
Books today and to any stable crawlable HTTP(S) image host in the future.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', re.I | re.S)
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',
    re.I,
)


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def get_meta(text: str, key: str, attr_name: str) -> str | None:
    key_l = key.lower()
    for m in META_TAG_RE.finditer(text):
        data = attrs(m.group(0))
        if data.get(attr_name.lower(), "").lower() == key_l:
            return data.get("content")
    return None


def set_meta(text: str, key: str, value: str, attr_name: str) -> str:
    key_l = key.lower()
    escaped = html.escape(value, quote=True)
    for m in META_TAG_RE.finditer(text):
        tag = m.group(0)
        data = attrs(tag)
        if data.get(attr_name.lower(), "").lower() != key_l:
            continue
        if "content" in data:
            new_tag = re.sub(
                r'''(\bcontent\s*=\s*)(["']).*?\2''',
                lambda x: f'{x.group(1)}"{escaped}"',
                tag,
                count=1,
                flags=re.I | re.S,
            )
        else:
            new_tag = tag[:-1] + f' content="{escaped}">'
        return text[: m.start()] + new_tag + text[m.end() :]

    new_tag = f'<meta {attr_name}="{html.escape(key, quote=True)}" content="{escaped}">'
    return text.replace("</head>", new_tag + "\n</head>", 1)


def set_attr(tag: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pat = re.compile(rf'''(\b{re.escape(name)}\s*=\s*)(["']).*?\2''', re.I | re.S)
    if pat.search(tag):
        return pat.sub(lambda m: f'{m.group(1)}"{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", fragment))).strip()


def canonical_value(text: str) -> str | None:
    m = CANONICAL_RE.search(text)
    return html.unescape(m.group(1)) if m else None


def iter_json_ld(text: str):
    for m in SCRIPT_RE.finditer(text):
        try:
            yield json.loads(m.group(2).strip())
        except json.JSONDecodeError:
            continue


def is_type(node: dict[str, Any], wanted: str) -> bool:
    node_type = node.get("@type")
    return node_type == wanted or (isinstance(node_type, list) and wanted in node_type)


def first_book_node(node: Any) -> dict[str, Any] | None:
    if isinstance(node, dict):
        if is_type(node, "Book"):
            return node
        for value in node.values():
            found = first_book_node(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = first_book_node(value)
            if found is not None:
                return found
    return None


def book_node_from_page(text: str) -> dict[str, Any] | None:
    for data in iter_json_ld(text):
        found = first_book_node(data)
        if found is not None:
            return found
    return None


def is_book_landing(text: str) -> bool:
    if (get_meta(text, "og:type", "property") or "").lower() == "book":
        return True
    return book_node_from_page(text) is not None


def locale_code(text: str, path: pathlib.Path) -> str:
    m = HTML_LANG_RE.search(text)
    if m:
        raw = m.group(1).lower().replace("_", "-")
        if raw.startswith("pt"):
            return "pt-br"
        return raw.split("-")[0]
    parts = {p.lower() for p in path.parts}
    for loc in ("ru", "tr", "de", "es", "fr", "pt-br"):
        if loc in parts:
            return loc
    return "en"


def book_title(text: str, path: pathlib.Path) -> str:
    node = book_node_from_page(text)
    if node and isinstance(node.get("name"), str) and node["name"].strip():
        return node["name"].strip()
    h1 = H1_RE.search(text)
    if h1:
        value = plain_text(h1.group(1))
        if value:
            return value
    og = get_meta(text, "og:title", "property")
    if og:
        return og.strip()
    return path.parent.name.replace("-", " ").strip()


def image_copy(locale: str, title: str) -> tuple[str, str]:
    templates = {
        "ru": (
            'Обложка книги «{title}» автора Faramarz Kowsari',
            '«{title}» — обложка книги автора Faramarz Kowsari',
        ),
        "tr": (
            '{title} — Faramarz Kowsari kitap kapağı',
            '{title} — Faramarz Kowsari tarafından yazılan kitabın kapağı',
        ),
        "de": (
            'Buchcover von „{title}“ von Faramarz Kowsari',
            '„{title}“ — Buchcover des Buches von Faramarz Kowsari',
        ),
        "es": (
            'Portada del libro «{title}» de Faramarz Kowsari',
            '«{title}» — portada del libro de Faramarz Kowsari',
        ),
        "fr": (
            'Couverture du livre «{title}» de Faramarz Kowsari',
            '«{title}» — couverture du livre de Faramarz Kowsari',
        ),
        "pt-br": (
            'Capa do livro “{title}”, de Faramarz Kowsari',
            '“{title}” — capa do livro de Faramarz Kowsari',
        ),
        "en": (
            'Book cover of {title} by Faramarz Kowsari',
            '{title} — book cover, by Faramarz Kowsari',
        ),
    }
    alt_t, caption_t = templates.get(locale, templates["en"])
    return alt_t.format(title=title), caption_t.format(title=title)


def ensure_large_image_preview(text: str) -> str:
    robots = get_meta(text, "robots", "name")
    if not robots:
        return set_meta(
            text,
            "robots",
            "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1",
            "name",
        )
    if "max-image-preview:" not in robots.lower():
        robots = robots.rstrip(" ,") + ",max-image-preview:large"
        return set_meta(text, "robots", robots, "name")
    return text


def update_cover_markup(text: str, cover: str, alt: str, caption: str) -> str:
    """Update the actual cover <img>, wherever localized templates place it."""
    for m in IMG_RE.finditer(text):
        tag = m.group(0)
        src = attrs(tag).get("src")
        if src != cover:
            continue
        new_tag = set_attr(tag, "alt", alt)
        new_tag = set_attr(new_tag, "itemprop", "image")
        new_tag = set_attr(new_tag, "title", caption)
        return text[: m.start()] + new_tag + text[m.end() :]
    return text


def mutate_schema(node: Any, canonical: str, cover: str, alt: str, caption: str) -> tuple[bool, bool]:
    found_book = False
    found_page = False
    image_id = canonical.rstrip("/") + "/#primaryimage"

    if isinstance(node, dict):
        if is_type(node, "Book"):
            node["image"] = {
                "@type": "ImageObject",
                "@id": image_id,
                "contentUrl": cover,
                "url": cover,
                "name": alt,
                "caption": caption,
                "representativeOfPage": True,
            }
            mep = node.get("mainEntityOfPage")
            if not isinstance(mep, dict):
                mep = {"@type": "WebPage", "@id": canonical}
                node["mainEntityOfPage"] = mep
            else:
                mep.setdefault("@type", "WebPage")
                mep.setdefault("@id", canonical)
            mep["primaryImageOfPage"] = {"@id": image_id}
            found_book = True

        if is_type(node, "WebPage"):
            node_url = node.get("url")
            node_id = node.get("@id")
            canonical_norm = canonical.rstrip("/")
            url_matches = isinstance(node_url, str) and node_url.rstrip("/") == canonical_norm
            id_matches = isinstance(node_id, str) and node_id.split("#", 1)[0].rstrip("/") == canonical_norm
            if url_matches or id_matches:
                node["primaryImageOfPage"] = {"@id": image_id}
                found_page = True

        for value in list(node.values()):
            if isinstance(value, (dict, list)):
                child_book, child_page = mutate_schema(value, canonical, cover, alt, caption)
                found_book = found_book or child_book
                found_page = found_page or child_page

    elif isinstance(node, list):
        for value in node:
            if isinstance(value, (dict, list)):
                child_book, child_page = mutate_schema(value, canonical, cover, alt, caption)
                found_book = found_book or child_book
                found_page = found_page or child_page

    return found_book, found_page


def update_json_ld(text: str, canonical: str, cover: str, alt: str, caption: str) -> str:
    found_book_anywhere = False

    def repl(m: re.Match[str]) -> str:
        nonlocal found_book_anywhere
        try:
            data = json.loads(m.group(2).strip())
        except json.JSONDecodeError:
            return m.group(0)
        found_book, _ = mutate_schema(data, canonical, cover, alt, caption)
        if not found_book:
            return m.group(0)
        found_book_anywhere = True
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return m.group(1) + payload + m.group(3)

    out = SCRIPT_RE.sub(repl, text)
    if found_book_anywhere:
        return out

    image_id = canonical.rstrip("/") + "/#primaryimage"
    fallback = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ImageObject",
                "@id": image_id,
                "contentUrl": cover,
                "url": cover,
                "name": alt,
                "caption": caption,
                "representativeOfPage": True,
            },
            {
                "@type": "WebPage",
                "@id": canonical,
                "url": canonical,
                "primaryImageOfPage": {"@id": image_id},
            },
        ],
    }
    block = (
        '<script type="application/ld+json">'
        + json.dumps(fallback, ensure_ascii=False, separators=(",", ":"))
        + "</script>\n"
    )
    return out.replace("</head>", block + "</head>", 1)


def process_page(path: pathlib.Path) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8")
    if not is_book_landing(text):
        return False, None

    canonical = canonical_value(text)
    if not canonical:
        return False, "missing canonical"

    cover = get_meta(text, "og:image", "property") or get_meta(text, "twitter:image", "name")
    if not cover or not re.match(r"^https?://", cover, re.I):
        return False, "missing external cover"

    title = book_title(text, path)
    locale = locale_code(text, path)
    alt, caption = image_copy(locale, title)

    out = text
    out = ensure_large_image_preview(out)
    out = set_meta(out, "og:image:alt", alt, "property")
    out = set_meta(out, "twitter:image:alt", alt, "name")
    out = update_cover_markup(out, cover, alt, caption)
    out = update_json_ld(out, canonical, cover, alt, caption)

    if out != text:
        path.write_text(out, encoding="utf-8")
        return True, None
    return False, None


def main() -> None:
    changed = 0
    eligible = 0
    skipped: list[tuple[str, str]] = []
    for path in sorted(BOOKS.rglob("index.html")):
        text = path.read_text(encoding="utf-8")
        if not is_book_landing(text):
            continue
        eligible += 1
        did_change, reason = process_page(path)
        changed += int(did_change)
        if reason:
            skipped.append((str(path.relative_to(ROOT)), reason))

    print(f"External-cover image SEO: {changed}/{eligible} individual book landing pages updated.")
    if skipped:
        for path, reason in skipped:
            print(f"SKIP {path}: {reason}")
        print(f"{len(skipped)} book page(s) lacked a usable external cover/canonical URL and were left unchanged.")


if __name__ == "__main__":
    main()
