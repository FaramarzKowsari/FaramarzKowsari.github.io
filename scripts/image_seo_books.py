#!/usr/bin/env python3
"""
Post-process generated book landing pages for image search without hosting
or downloading any book cover in this repository.

The cover URL remains external (Google Books, Pinterest, CDN, publisher site,
etc.). This script only strengthens the semantic signals on each HTML page.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
AUTHOR = "Faramarz Kowsari"

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', re.I | re.S)
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)
BOOK_TOP_RE = re.compile(
    r'(<section\b[^>]*class=["\'][^"\']*\bbook-top\b[^"\']*["\'][^>]*>)(.*?)(</section>)',
    re.I | re.S,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def get_meta(text: str, key: str, attr_name: str | None = None) -> str | None:
    key_l = key.lower()
    for m in META_TAG_RE.finditer(text):
        data = attrs(m.group(0))
        if attr_name:
            if data.get(attr_name.lower(), "").lower() == key_l:
                return data.get("content")
        elif data.get("property", "").lower() == key_l or data.get("name", "").lower() == key_l:
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
    alt_t, cap_t = templates.get(locale, templates["en"])
    return alt_t.format(title=title), cap_t.format(title=title)


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


def update_cover_markup(text: str, alt: str, caption: str) -> str:
    m = BOOK_TOP_RE.search(text)
    if not m:
        return text
    body = m.group(2)
    img_m = IMG_RE.search(body)
    if not img_m:
        return text
    img = set_attr(img_m.group(0), "alt", alt)
    img = set_attr(img, "itemprop", "image")
    figure = (
        '<figure class="book-cover-figure">\n'
        f'    {img}\n'
        f'    <figcaption class="book-cover-caption">{html.escape(caption)}</figcaption>\n'
        "  </figure>"
    )
    if "book-cover-figure" in body:
        body = re.sub(
            r'<figure\b[^>]*class=["\'][^"\']*\bbook-cover-figure\b[^"\']*["\'][^>]*>.*?</figure>',
            figure,
            body,
            count=1,
            flags=re.I | re.S,
        )
    else:
        body = body[: img_m.start()] + figure + body[img_m.end() :]
    return text[: m.start()] + m.group(1) + body + m.group(3) + text[m.end() :]


def mutate_book_schema(node: Any, canonical: str, cover: str, alt: str, caption: str) -> bool:
    changed = False
    if isinstance(node, dict):
        node_type = node.get("@type")
        is_book = node_type == "Book" or (isinstance(node_type, list) and "Book" in node_type)
        if is_book:
            image_id = canonical.rstrip("/") + "/#primaryimage"
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
            changed = True
        for value in node.values():
            if isinstance(value, (dict, list)):
                changed = mutate_book_schema(value, canonical, cover, alt, caption) or changed
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                changed = mutate_book_schema(item, canonical, cover, alt, caption) or changed
    return changed


def update_json_ld(text: str, canonical: str, cover: str, alt: str, caption: str) -> str:
    found_book = False

    def repl(m: re.Match[str]) -> str:
        nonlocal found_book
        raw = m.group(2).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return m.group(0)
        if mutate_book_schema(data, canonical, cover, alt, caption):
            found_book = True
            payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            return m.group(1) + payload + m.group(3)
        return m.group(0)

    text = SCRIPT_RE.sub(repl, text)
    if found_book:
        return text

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
    return text.replace("</head>", block + "</head>", 1)


def process_page(path: pathlib.Path) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8")
    if (get_meta(text, "og:type", "property") or "").lower() != "book":
        return False, None

    link_m = re.search(
        r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',
        text,
        re.I,
    )
    canonical = html.unescape(link_m.group(1)) if link_m else None
    if not canonical:
        return False, "missing canonical"

    cover = get_meta(text, "og:image", "property") or get_meta(text, "twitter:image", "name")
    if not cover or not re.match(r"^https?://", cover, re.I):
        return False, "missing external cover"

    title = get_meta(text, "og:title", "property")
    if not title:
        h1 = H1_RE.search(text)
        title = plain_text(h1.group(1)) if h1 else ""
    title = (title or path.parent.name.replace("-", " ")).strip()

    locale = locale_code(text, path)
    alt, caption = image_copy(locale, title)

    out = text
    out = ensure_large_image_preview(out)
    out = set_meta(out, "og:image:alt", alt, "property")
    out = set_meta(out, "twitter:image:alt", alt, "name")
    out = update_cover_markup(out, alt, caption)
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
        if (get_meta(text, "og:type", "property") or "").lower() != "book":
            continue
        eligible += 1
        did_change, reason = process_page(path)
        changed += int(did_change)
        if reason:
            skipped.append((str(path.relative_to(ROOT)), reason))

    print(f"External-cover image SEO: {changed}/{eligible} book pages updated.")
    if skipped:
        for path, reason in skipped:
            print(f"SKIP {path}: {reason}")
        print(f"{len(skipped)} book page(s) had no usable external cover/canonical URL and were left unchanged.")


if __name__ == "__main__":
    main()
