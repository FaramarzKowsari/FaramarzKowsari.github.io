#!/usr/bin/env python3
"""Quality gate for the external Google Books cover image SEO layer.

This gate intentionally requires covers to remain on Google Books. It verifies
that every public book page, localized page, index surface, schema object and
image sitemap converges on the same external cover URL, while preserving the
visible Faramarz Kowsari byline directly under each book title.
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
DATA = BOOKS / "books.json"
COVER_INDEX = BOOKS / "google-books-cover-index.json"
BOOKS_INDEX = BOOKS / "index.html"
TOPICS_INDEX = BOOKS / "topics" / "index.html"
IMAGE_SITEMAP = BOOKS / "image-sitemap.xml"
GALLERY_SITEMAP = BOOKS / "sitemap-cover-gallery.xml"
AUTHOR_URL = "https://faramarzkowsari.github.io/books/author/"
AUTHOR = "Faramarz Kowsari"

META_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', re.I | re.S)
SCRIPT_RE = re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
CANONICAL_RE = re.compile(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', re.I)


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def meta_value(text: str, key: str, attr_name: str) -> str:
    key_l = key.lower()
    for match in META_RE.finditer(text):
        data = attrs(match.group(0))
        if data.get(attr_name.lower(), "").lower() == key_l:
            return data.get("content", "")
    return ""


def canonical_value(text: str) -> str:
    match = CANONICAL_RE.search(text)
    return html.unescape(match.group(1)).strip() if match else ""


def json_payloads(text: str):
    for match in SCRIPT_RE.finditer(text):
        try:
            yield json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue


def type_has(node: dict, wanted: str) -> bool:
    value = node.get("@type")
    return wanted in value if isinstance(value, list) else value == wanted


def walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(v for v in current.values() if isinstance(v, (dict, list)))
        elif isinstance(current, list):
            stack.extend(v for v in current if isinstance(v, (dict, list)))


def first_book_node(text: str):
    for payload in json_payloads(text):
        for node in walk(payload):
            if type_has(node, "Book"):
                return node
    return None


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", fragment))).strip()


def is_google_books_cover(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host in {"books.google.com", "books.googleusercontent.com"} and "/books/content" in parts.path:
        return True
    return host == "play.google.com" and parts.path.startswith("/books/publisher/content/images/frontcover/")


def book_title(text: str, node: dict | None, fallback: str) -> str:
    if isinstance(node, dict) and clean(node.get("name")):
        return clean(node.get("name"))
    match = H1_RE.search(text)
    if match:
        title = plain_text(match.group(1))
        if title:
            return title
    return fallback


def has_exact_cover_img(text: str, cover: str, title: str) -> tuple[bool, str]:
    for match in IMG_RE.finditer(text):
        data = attrs(match.group(0))
        if clean(data.get("src")) != cover:
            continue
        alt = clean(data.get("alt"))
        if not alt:
            return False, "visible cover IMG has no ALT"
        if title and title.casefold() not in alt.casefold():
            return False, "visible cover ALT does not contain the book title"
        if AUTHOR.casefold() not in alt.casefold():
            return False, "visible cover ALT does not identify Faramarz Kowsari"
        if clean(data.get("itemprop")).casefold() != "image":
            return False, "visible cover IMG is missing itemprop=image"
        if clean(data.get("fetchpriority")).casefold() != "high":
            return False, "visible cover IMG is missing fetchpriority=high"
        return True, ""
    return False, "visible cover IMG does not use the canonical Google Books URL"


def schema_cover_ok(node: dict | None, cover: str, canonical: str) -> tuple[bool, str]:
    if not isinstance(node, dict):
        return False, "Book JSON-LD missing"
    image = node.get("image")
    if not isinstance(image, dict):
        return False, "Book.image is not an ImageObject"
    image_id = canonical.rstrip("/") + "/#primaryimage"
    if clean(image.get("@type")) != "ImageObject":
        return False, "Book.image @type is not ImageObject"
    if clean(image.get("@id")) != image_id:
        return False, "Book.image @id mismatch"
    if clean(image.get("contentUrl")) != cover or clean(image.get("url")) != cover:
        return False, "Book.image does not use the canonical Google Books cover"
    if not image.get("representativeOfPage"):
        return False, "Book.image representativeOfPage is not true"
    mep = node.get("mainEntityOfPage")
    if not isinstance(mep, dict):
        return False, "Book.mainEntityOfPage is missing"
    primary = mep.get("primaryImageOfPage")
    if not isinstance(primary, dict) or clean(primary.get("@id")) != image_id:
        return False, "primaryImageOfPage does not reference the canonical ImageObject"
    return True, ""


def validate_page(path: pathlib.Path, expected_cover: str, label: str, fallback_title: str, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    canonical = canonical_value(text)
    if not canonical:
        errors.append(f"{label}: canonical URL missing")
        return

    og = clean(meta_value(text, "og:image", "property"))
    tw = clean(meta_value(text, "twitter:image", "name"))
    if og != expected_cover:
        errors.append(f"{label}: og:image is not the canonical Google Books cover")
    if tw != expected_cover:
        errors.append(f"{label}: twitter:image is not the canonical Google Books cover")

    robots = clean(meta_value(text, "robots", "name")).lower()
    if "max-image-preview:large" not in robots:
        errors.append(f"{label}: max-image-preview:large missing")

    node = first_book_node(text)
    title = book_title(text, node, fallback_title)
    ok, reason = schema_cover_ok(node, expected_cover, canonical)
    if not ok:
        errors.append(f"{label}: {reason}")

    ok, reason = has_exact_cover_img(text, expected_cover, title)
    if not ok:
        errors.append(f"{label}: {reason}")

    # The author's visible name must remain directly beneath the title.
    byline = re.search(
        r'<!-- author-visible:start -->(.*?)<!-- author-visible:end -->',
        text,
        re.I | re.S,
    )
    if not byline:
        errors.append(f"{label}: visible author byline missing")
    else:
        block = html.unescape(byline.group(1))
        if AUTHOR not in block or AUTHOR_URL not in block:
            errors.append(f"{label}: visible Faramarz Kowsari byline/link is incomplete")


books = load_json(DATA, [])
cover_index = load_json(COVER_INDEX, {})
errors: list[str] = []
warnings: list[str] = []
checked = 0
localized_checked = 0

if not isinstance(books, list):
    errors.append("books/books.json is not a JSON array")
    books = []
if not isinstance(cover_index, dict):
    errors.append("books/google-books-cover-index.json is invalid")
    cover_index = {}

index_text = BOOKS_INDEX.read_text(encoding="utf-8") if BOOKS_INDEX.exists() else ""
topics_text = TOPICS_INDEX.read_text(encoding="utf-8") if TOPICS_INDEX.exists() else ""
gallery_text = ""
for gallery_page in sorted((BOOKS / "covers").rglob("index.html")) if (BOOKS / "covers").exists() else []:
    gallery_text += gallery_page.read_text(encoding="utf-8") + "\n"
image_sitemap_text = IMAGE_SITEMAP.read_text(encoding="utf-8") if IMAGE_SITEMAP.exists() else ""

if not BOOKS_INDEX.exists():
    errors.append("books index missing")
if not TOPICS_INDEX.exists():
    errors.append("topics index missing")
if not gallery_text:
    errors.append("Google Books cover gallery missing")
if not IMAGE_SITEMAP.exists():
    errors.append("books/image-sitemap.xml missing")
if not GALLERY_SITEMAP.exists():
    errors.append("books/sitemap-cover-gallery.xml missing")

local_cover_dir = BOOKS / "images" / "covers"
if local_cover_dir.exists():
    local_cover_files = [
        p for p in local_cover_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
    ]
    if local_cover_files:
        errors.append(
            f"self-hosted book covers are forbidden: {len(local_cover_files)} file(s) found under books/images/covers"
        )

for book in books:
    if not isinstance(book, dict) or book.get("status", "active") != "active":
        continue
    slug = clean(book.get("slug"))
    gid = clean(book.get("google_books_id"))
    path = BOOKS / slug / "index.html" if slug else None
    if not slug or not gid or path is None or not path.exists():
        continue

    entry = cover_index.get(gid) if isinstance(cover_index.get(gid), dict) else {}
    expected_cover = clean(entry.get("url")) or clean(book.get("cover_url"))
    if not is_google_books_cover(expected_cover):
        errors.append(f"{slug}: cover must remain externally hosted on Google Books")
        continue
    if not entry:
        warnings.append(f"{slug}: best-cover API cache unresolved; catalog Google Books cover is being used")

    checked += 1
    validate_page(path, expected_cover, slug, clean(book.get("title")), errors)

    escaped_cover = html.escape(expected_cover, quote=True)
    book_url = f"https://faramarzkowsari.github.io/books/{slug}/"
    if index_text:
        index_link_present = f'./{slug}/' in index_text
        if index_link_present and escaped_cover not in index_text:
            errors.append(f"{slug}: books index links the book but not its canonical Google-hosted cover")
        elif not index_link_present:
            warnings.append(f"{slug}: book is not currently listed in the main visual books index")
    if topics_text:
        topic_link_present = f'../{slug}/' in topics_text
        if topic_link_present and escaped_cover not in topics_text:
            errors.append(f"{slug}: topic index links the book but not its canonical Google-hosted cover")
        elif not topic_link_present:
            warnings.append(f"{slug}: book is not currently listed in the broad topic index")
    if gallery_text and (escaped_cover not in gallery_text or book_url not in gallery_text):
        errors.append(f"{slug}: cover gallery does not connect the canonical cover to the book page")

    escaped_xml_cover = html.escape(expected_cover, quote=False)
    if image_sitemap_text and (book_url not in image_sitemap_text or escaped_xml_cover not in image_sitemap_text):
        errors.append(f"{slug}: image sitemap does not pair the book page with its canonical Google Books cover")

    book_root = BOOKS / slug
    for child in sorted(book_root.iterdir()):
        localized = child / "index.html"
        if not child.is_dir() or not localized.exists():
            continue
        localized_checked += 1
        validate_page(localized, expected_cover, f"{slug}/{child.name}", clean(book.get("title")), errors)

print(
    f"Google Books Image SEO gate checked {checked} base book page(s) and "
    f"{localized_checked} localized page(s); covers remain externally hosted on Google Books."
)
for item in warnings[:60]:
    print("WARNING:", item)
if len(warnings) > 60:
    print(f"WARNING: {len(warnings) - 60} additional warning(s) omitted.")

if errors:
    for item in errors[:140]:
        print("ERROR:", item)
    if len(errors) > 140:
        print(f"ERROR: {len(errors) - 140} additional error(s) omitted.")
    print(f"Google Books Image SEO gate FAILED with {len(errors)} error(s).")
    sys.exit(1)

print(f"Google Books Image SEO gate PASSED with {len(warnings)} warning(s).")
