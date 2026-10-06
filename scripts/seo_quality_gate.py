#!/usr/bin/env python3
"""Fail the book build when durable SEO and author-entity invariants are missing.

The gate checks technical completeness, not rankings. Search position can never be
guaranteed, but every public book page should expose a consistent, crawlable set
of signals: canonical URL, description, semantic Book data, breadcrumbs,
localized alternates, cover semantics, internal related links, topic-hub
membership, and one canonical Faramarz Kowsari Person entity.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
SEO_DATA = BOOKS / "seo-keywords.json"
ENTITY_FILE = BOOKS / "author" / "entity.json"
AUTHOR_PAGE = BOOKS / "author" / "index.html"
ROOT_INDEX = ROOT / "index.html"
BOOKS_INDEX = BOOKS / "index.html"
BOOKS_BASE = "https://faramarzkowsari.github.io/books"
PERSIAN_AUTHOR_NAME = "فرامرز کوثری"

SCRIPT_RE = re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
META_RE = re.compile(r'<meta\b[^>]*>', re.I)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', re.I | re.S)


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def type_has(node, wanted):
    if not isinstance(node, dict):
        return False
    value = node.get("@type")
    return wanted in value if isinstance(value, list) else value == wanted


def meta_value(text, key, attr="name"):
    for m in META_RE.finditer(text):
        attrs = {a.group(1).lower(): html.unescape(a.group(3)) for a in ATTR_RE.finditer(m.group(0))}
        if attrs.get(attr, "").lower() == key.lower():
            return attrs.get("content", "")
    return ""


def canonical(text):
    m = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', text, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def json_payloads(text):
    out = []
    for m in SCRIPT_RE.finditer(text):
        try:
            out.append(json.loads(m.group(1).strip()))
        except json.JSONDecodeError:
            continue
    return out


def walk_nodes(payload):
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            yield node
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)


def json_types(text):
    found = []
    for payload in json_payloads(text):
        for node in walk_nodes(payload):
            t = node.get("@type")
            if isinstance(t, list):
                found.extend(str(x) for x in t)
            elif t:
                found.append(str(t))
    return found


def nodes_of_type(text, wanted):
    out = []
    for payload in json_payloads(text):
        for node in walk_nodes(payload):
            if type_has(node, wanted):
                out.append(node)
    return out


def book_nodes(text):
    return nodes_of_type(text, "Book")


def person_nodes(text, person_id=None):
    nodes = nodes_of_type(text, "Person")
    if person_id is None:
        return nodes
    return [node for node in nodes if node.get("@id") == person_id]


def has_cover_alt(text, cover):
    if not cover:
        return True
    fallback = False
    for m in re.finditer(r'<img\b[^>]*>', text, re.I):
        tag = html.unescape(m.group(0))
        am = re.search(r'\balt=["\']([^"\']*)', tag, re.I)
        has_alt = bool(am and clean(am.group(1)))
        fallback = fallback or has_alt
        if "books.google.com/books/content" in tag or cover.split("&", 1)[0] in tag:
            return has_alt
    return fallback


def has_author_link(text, author_url):
    for m in re.finditer(r'<link\b[^>]*>', text, re.I):
        tag = m.group(0)
        if re.search(r'\brel=["\']author["\']', tag, re.I) and author_url in html.unescape(tag):
            return True
    return False


def validate_book_author(node, slug, entity, errors):
    author = node.get("author")
    if not isinstance(author, dict):
        errors.append(f"{slug}: Book schema author is not a Person object")
        return
    if author.get("@id") != entity["person_id"]:
        errors.append(f"{slug}: Book.author @id is not canonical Person ID")
    if clean(author.get("name")) != entity["name"]:
        errors.append(f"{slug}: Book.author canonical name mismatch")
    if clean(author.get("url")) != entity["author_page"]:
        errors.append(f"{slug}: Book.author URL does not point to canonical author page")
    alt = author.get("alternateName") or []
    if isinstance(alt, str):
        alt = [alt]
    if PERSIAN_AUTHOR_NAME in alt:
        errors.append(f"{slug}: Persian author name must not appear in Book.author")
    if clean(author.get("image")) != entity["image"]:
        errors.append(f"{slug}: Book.author canonical portrait mismatch")


def validate_author_surface(text, label, entity, errors):
    if clean(meta_value(text, "author")) != entity["name"]:
        errors.append(f"{label}: meta author missing or mismatched")
    if not has_author_link(text, entity["author_page"]):
        errors.append(f"{label}: rel=author link to canonical profile missing")


books = load(DATA, [])
profiles = load(SEO_DATA, {})
entity = load(ENTITY_FILE, {})
errors = []
warnings = []
checked = 0
localized_checked = 0
author_linked = 0

if not isinstance(books, list):
    errors.append("books/books.json is not a JSON array")
if not isinstance(profiles, dict):
    errors.append("books/seo-keywords.json is not a JSON object")
if not isinstance(entity, dict) or not entity:
    errors.append("books/author/entity.json is missing or invalid")

required_entity = {
    "person_id": "https://faramarzkowsari.github.io/#person",
    "name": "Faramarz Kowsari",
    "author_page": "https://faramarzkowsari.github.io/books/author/",
    "website": "https://faramarzkowsari.github.io/",
    "orcid": "0000-0003-1692-0453",
}
for key, expected in required_entity.items():
    if clean(entity.get(key)) != expected:
        errors.append(f"author entity: {key} must be {expected!r}")
if PERSIAN_AUTHOR_NAME in (entity.get("alternate_name") or []):
    errors.append("author entity: Persian author name must not be exposed in book-facing entity data")
if not clean(entity.get("image")):
    errors.append("author entity: canonical portrait URL is missing")

required_profiles = {
    "google_play_books",
    "google_scholar",
    "github",
    "linkedin",
    "orcid",
    "official_website",
}
profile_map = entity.get("profiles") if isinstance(entity.get("profiles"), dict) else {}
for key in sorted(required_profiles):
    if not clean(profile_map.get(key)):
        errors.append(f"author entity: profile {key} is missing")

required_same_as = {
    "https://scholar.google.com/citations?user=G7tP5WMAAAAJ&hl=en",
    "https://github.com/FaramarzKowsari",
    "https://www.linkedin.com/in/faramarzkowsari",
    "https://orcid.org/0000-0003-1692-0453",
}
same_as = set(entity.get("same_as") or [])
for url in sorted(required_same_as):
    if url not in same_as:
        errors.append(f"author entity: sameAs missing {url}")

image_url = clean(entity.get("image"))
if image_url:
    expected_prefix = "https://faramarzkowsari.github.io/books/"
    if image_url.startswith(expected_prefix):
        local_image = BOOKS / image_url[len(expected_prefix):]
        if not local_image.exists():
            errors.append(f"author entity: canonical portrait file missing ({local_image.relative_to(ROOT)})")
    else:
        warnings.append("author entity: canonical portrait is not hosted on the official site")

if not AUTHOR_PAGE.exists():
    errors.append("books/author/index.html missing")
else:
    author_text = AUTHOR_PAGE.read_text(encoding="utf-8")
    if canonical(author_text) != required_entity["author_page"]:
        errors.append("author page: canonical URL mismatch")
    validate_author_surface(author_text, "author page", entity, errors)
    if "ProfilePage" not in json_types(author_text):
        errors.append("author page: ProfilePage JSON-LD missing")
    people = person_nodes(author_text, entity.get("person_id"))
    if not people:
        errors.append("author page: canonical Person JSON-LD missing")
    else:
        person = people[0]
        if clean(person.get("name")) != entity.get("name"):
            errors.append("author page: Person name mismatch")
        alt = person.get("alternateName") or []
        if isinstance(alt, str):
            alt = [alt]
        if PERSIAN_AUTHOR_NAME in alt:
            errors.append("author page: Persian author name remains in Person alternateName")
        if clean(person.get("image")) != image_url:
            errors.append("author page: Person image is not the canonical portrait")
        person_same_as = set(person.get("sameAs") or [])
        for url in required_same_as:
            if url not in person_same_as:
                errors.append(f"author page: Person sameAs missing {url}")
    if image_url and image_url not in author_text:
        errors.append("author page: canonical portrait is not visible/referenced")
    if PERSIAN_AUTHOR_NAME in author_text:
        errors.append("author page: Persian author name must not be visible or embedded")

if not ROOT_INDEX.exists():
    errors.append("root index.html missing")
else:
    root_text = ROOT_INDEX.read_text(encoding="utf-8")
    validate_author_surface(root_text, "root index", entity, errors)
    root_people = person_nodes(root_text, entity.get("person_id"))
    if not root_people:
        errors.append("root index: canonical Person JSON-LD missing")
    else:
        person = root_people[0]
        if clean(person.get("image")) != image_url:
            errors.append("root index: Person portrait does not match canonical author image")
        alt = person.get("alternateName") or []
        if isinstance(alt, str):
            alt = [alt]
        if PERSIAN_AUTHOR_NAME in alt:
            errors.append("root index: Persian author name remains in Person alternateName")

if not BOOKS_INDEX.exists():
    errors.append("books/index.html missing")
else:
    index_text = BOOKS_INDEX.read_text(encoding="utf-8")
    validate_author_surface(index_text, "books index", entity, errors)
    collections = [n for n in nodes_of_type(index_text, "CollectionPage") if n.get("@id") == f"{BOOKS_BASE}/#collection"]
    if not collections:
        errors.append("books index: CollectionPage JSON-LD missing")
    elif collections[0].get("author") != {"@id": entity.get("person_id")}:
        errors.append("books index: CollectionPage.author does not reference canonical Person")
    if "Books by Faramarz Kowsari" not in index_text:
        errors.append("books index: single collection-level author heading missing")
    if entity.get("author_page") not in index_text:
        errors.append("books index: author profile link missing")
    if PERSIAN_AUTHOR_NAME in index_text:
        errors.append("books index: Persian author name must not be visible or embedded")

for book in books if isinstance(books, list) else []:
    slug = clean(book.get("slug"))
    if not slug or book.get("status", "active") != "active":
        continue
    path = BOOKS / slug / "index.html"
    if not path.exists():
        continue
    checked += 1
    profile = profiles.get(slug)
    if not isinstance(profile, dict):
        errors.append(f"{slug}: missing semantic SEO profile")
        continue
    if not clean(profile.get("primary_query")):
        errors.append(f"{slug}: missing primary query")
    if len(profile.get("secondary_queries") or []) < 2:
        errors.append(f"{slug}: fewer than 2 secondary queries")
    if len(profile.get("long_tail_queries") or []) < 2:
        errors.append(f"{slug}: fewer than 2 long-tail queries")
    if not profile.get("cluster"):
        errors.append(f"{slug}: missing topic cluster")
    if len(profile.get("related_slugs") or []) < 1 and len(profiles) > 1:
        warnings.append(f"{slug}: no semantic related books")

    gid = clean(book.get("google_books_id"))
    if gid:
        if not clean(book.get("google_books_url")):
            errors.append(f"{slug}: Google Books URL missing")
        if not clean(book.get("cover_url")):
            errors.append(f"{slug}: external Google Books cover missing")

    text = path.read_text(encoding="utf-8")
    if PERSIAN_AUTHOR_NAME in text:
        errors.append(f"{slug}: Persian author name must not appear on book pages")
    expected = f"{BOOKS_BASE}/{slug}/"
    if canonical(text) != expected:
        errors.append(f"{slug}: canonical mismatch ({canonical(text)!r})")
    desc = meta_value(text, "description")
    if not clean(desc):
        errors.append(f"{slug}: meta description missing")
    elif len(clean(desc)) < 55:
        warnings.append(f"{slug}: meta description is very short ({len(clean(desc))})")
    if re.search(r'<meta\b[^>]*name=["\']keywords["\']', text, re.I):
        errors.append(f"{slug}: obsolete meta keywords tag remains")
    if "<!-- semantic-seo:start -->" not in text:
        errors.append(f"{slug}: semantic SEO head block missing")
    types = json_types(text)
    if "Book" not in types:
        errors.append(f"{slug}: Book JSON-LD missing")
    if "BreadcrumbList" not in types:
        errors.append(f"{slug}: BreadcrumbList JSON-LD missing")
    nodes = book_nodes(text)
    if nodes:
        node = nodes[0]
        if not node.get("keywords"):
            errors.append(f"{slug}: Book schema keywords missing")
        if not node.get("about"):
            errors.append(f"{slug}: Book schema about entities missing")
        validate_book_author(node, slug, entity, errors)
    if clean(book.get("cover_url")) and not has_cover_alt(text, clean(book.get("cover_url"))):
        errors.append(f"{slug}: cover image ALT missing")
    if 'hreflang="x-default"' not in text:
        errors.append(f"{slug}: x-default hreflang missing")
    if profile.get("related_slugs") and "<!-- semantic-related-books:start -->" not in text:
        errors.append(f"{slug}: semantic related-books block missing")

    validate_author_surface(text, slug, entity, errors)
    if "<!-- author-entity:start -->" not in text:
        errors.append(f"{slug}: Author Entity head block missing")
    if "<!-- author-visible:start -->" not in text:
        errors.append(f"{slug}: compact visible author byline missing")
    elif entity.get("author_page") not in text:
        errors.append(f"{slug}: visible author byline does not link to author profile")
    else:
        author_linked += 1

    for loc in ("ru", "tr", "de", "es", "fr", "pt-br"):
        lp = BOOKS / slug / loc / "index.html"
        if not lp.exists():
            continue
        localized_checked += 1
        lt = lp.read_text(encoding="utf-8")
        label = f"{slug}/{loc}"
        if PERSIAN_AUTHOR_NAME in lt:
            errors.append(f"{label}: Persian author name must not appear on localized book pages")
        if not clean(meta_value(lt, "description")):
            errors.append(f"{label}: meta description missing")
        if re.search(r'<meta\b[^>]*name=["\']keywords["\']', lt, re.I):
            errors.append(f"{label}: obsolete meta keywords tag remains")
        ltypes = json_types(lt)
        if "Book" not in ltypes:
            errors.append(f"{label}: nested Book schema missing")
        if "BreadcrumbList" not in ltypes:
            errors.append(f"{label}: BreadcrumbList missing")
        lnodes = book_nodes(lt)
        if lnodes:
            if not lnodes[0].get("keywords"):
                errors.append(f"{label}: localized schema keywords missing")
            validate_book_author(lnodes[0], label, entity, errors)
        if profile.get("related_slugs") and "<!-- semantic-related-books:start -->" not in lt:
            errors.append(f"{label}: localized related-books block missing")
        validate_author_surface(lt, label, entity, errors)
        if "<!-- author-entity:start -->" not in lt:
            errors.append(f"{label}: Author Entity head block missing")
        if "<!-- author-visible:start -->" not in lt:
            errors.append(f"{label}: compact visible author byline missing")
        elif entity.get("author_page") not in lt:
            errors.append(f"{label}: visible author byline does not link to author profile")
        else:
            author_linked += 1

if not (BOOKS / "topics" / "index.html").exists():
    errors.append("topics index missing")
elif "<!-- semantic-topic-hubs:start -->" not in (BOOKS / "topics" / "index.html").read_text(encoding="utf-8"):
    errors.append("topics index is not linked to semantic topic hubs")
if not (BOOKS / "sitemap-topics.xml").exists():
    errors.append("books/sitemap-topics.xml missing")
if (BOOKS / "sitemap.xml").exists():
    sitemap_text = (BOOKS / "sitemap.xml").read_text(encoding="utf-8")
    if entity.get("author_page") not in sitemap_text:
        errors.append("books/sitemap.xml does not include the canonical author page")
else:
    errors.append("books/sitemap.xml missing")

print(
    f"SEO + Entity quality gate checked {checked} base book pages and "
    f"{localized_checked} localized book pages; {author_linked} pages expose the compact author link."
)
for item in warnings[:50]:
    print("WARNING:", item)
if len(warnings) > 50:
    print(f"WARNING: {len(warnings) - 50} additional warning(s) omitted.")

if errors:
    for item in errors[:120]:
        print("ERROR:", item)
    if len(errors) > 120:
        print(f"ERROR: {len(errors) - 120} additional error(s) omitted.")
    print(f"SEO + Entity quality gate FAILED with {len(errors)} error(s).")
    sys.exit(1)

print(f"SEO + Entity quality gate PASSED with {len(warnings)} warning(s).")
