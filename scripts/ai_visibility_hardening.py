#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
SITE = "https://faramarzkowsari.github.io"
BOOKS_BASE = f"{SITE}/books"
AUTHOR_URL = f"{BOOKS_BASE}/author/"
CATALOG = BOOKS / "catalog.json"
LLMS = ROOT / "llms.txt"
LLMS_FULL = ROOT / "llms-full.txt"

START = "<!-- ai-visibility:start -->"
END = "<!-- ai-visibility:end -->"


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def discovery_block() -> str:
    return (
        f"\n{START}\n"
        f'<link rel="alternate" type="text/plain" href="{SITE}/llms.txt" title="LLM-readable site index">\n'
        f'<link rel="alternate" type="text/plain" href="{SITE}/llms-full.txt" title="Expanded LLM-readable books index">\n'
        f'<link rel="alternate" type="application/json" href="{BOOKS_BASE}/catalog.json" title="Machine-readable books catalog">\n'
        f'<link rel="author" href="{AUTHOR_URL}" title="Faramarz Kowsari author profile">\n'
        f"{END}\n"
    )


def ensure_robots_meta(text: str) -> str:
    wanted = '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">'
    pattern = re.compile(r'<meta\s+name=["\']robots["\'][^>]*>', re.I)
    if pattern.search(text):
        return pattern.sub(wanted, text, count=1)
    return text.replace("</head>", wanted + "\n</head>", 1)


def patch_head(path: pathlib.Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", text, flags=re.S)
    text = ensure_robots_meta(text)
    text = text.replace("</head>", discovery_block() + "</head>", 1)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def canonical_from_html(text: str, path: pathlib.Path) -> str:
    match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', text, re.I)
    if match:
        return html.unescape(match.group(1)).strip()
    try:
        relative = path.parent.relative_to(ROOT).as_posix().strip("/")
    except ValueError:
        return f"{SITE}/"
    return f"{SITE}/{relative}/" if relative else f"{SITE}/"


def update_book_schema(path: pathlib.Path, catalog_by_slug: dict[str, dict]) -> bool:
    if not path.exists():
        return False
    slug = path.parent.name
    book_meta = catalog_by_slug.get(slug, {})
    text = path.read_text(encoding="utf-8")
    original = text
    canonical = canonical_from_html(text, path)

    pattern = re.compile(r'(<script\s+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)', re.I | re.S)

    def repl(match):
        raw = match.group(2).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)

        changed = False
        targets = []
        if isinstance(payload, dict):
            if payload.get("@type") == "Book":
                targets.append(payload)
            graph = payload.get("@graph")
            if isinstance(graph, list):
                targets.extend(item for item in graph if isinstance(item, dict) and item.get("@type") == "Book")

        for book in targets:
            desired_author = {
                "@type": "Person",
                "@id": f"{SITE}/#person",
                "name": "Faramarz Kowsari",
                "url": AUTHOR_URL,
            }
            updates = {
                "@id": f"{canonical}#book",
                "author": desired_author,
                "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
                "isPartOf": {
                    "@type": "CollectionPage",
                    "@id": f"{BOOKS_BASE}/#collection",
                    "name": "Books by Faramarz Kowsari",
                    "url": f"{BOOKS_BASE}/",
                },
            }
            topics = [clean(x) for x in (book_meta.get("key_topics") or []) if clean(x)]
            if topics:
                updates["keywords"] = topics[:30]
            for key, value in updates.items():
                if book.get(key) != value:
                    book[key] = value
                    changed = True

        if not changed:
            return match.group(0)
        return match.group(1) + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + match.group(3)

    text = pattern.sub(repl, text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def enrich_catalog(catalog: dict) -> bool:
    if not isinstance(catalog, dict):
        return False
    original = json.dumps(catalog, ensure_ascii=False, sort_keys=True)
    catalog["llms_index"] = f"{SITE}/llms.txt"
    catalog["llms_full"] = f"{SITE}/llms-full.txt"
    catalog["robots"] = f"{SITE}/robots.txt"
    catalog["master_sitemap"] = f"{SITE}/sitemap.xml"
    catalog["discovery"] = {
        "search_and_answer_engines": "Public canonical pages are crawlable and intended for search/answer-engine discovery.",
        "canonical_html": f"{BOOKS_BASE}/all-books/",
        "machine_readable_catalog": f"{BOOKS_BASE}/catalog.json",
    }
    new = json.dumps(catalog, ensure_ascii=False, sort_keys=True)
    if new == original:
        return False
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def write_llms_full(catalog: dict) -> None:
    books = catalog.get("books", []) if isinstance(catalog, dict) else []
    lines = [
        "# Faramarz Kowsari — Expanded Books and Source Index",
        "",
        "> Full machine-readable text companion for the official public books library. Canonical HTML pages remain the authoritative public pages.",
        "",
        f"- Official website: {SITE}/",
        f"- Author profile: {AUTHOR_URL}",
        f"- Books library: {BOOKS_BASE}/",
        f"- Text-first catalog: {BOOKS_BASE}/all-books/",
        f"- JSON catalog: {BOOKS_BASE}/catalog.json",
        f"- Books sitemap: {BOOKS_BASE}/sitemap.xml",
        f"- Master sitemap: {SITE}/sitemap.xml",
        f"- robots.txt: {SITE}/robots.txt",
        "",
        "## Author identity",
        "",
        "- Name: Faramarz Kowsari",
        "- ORCID: https://orcid.org/0000-0003-1692-0453",
        "- Google Scholar: https://scholar.google.com/citations?user=G7tP5WMAAAAJ&hl=en",
        "- GitHub: https://github.com/FaramarzKowsari",
        "- LinkedIn: https://www.linkedin.com/in/faramarzkowsari",
        "- Instagram: https://www.instagram.com/faramarzkowsari/",
        "- Zenodo project DOI: https://doi.org/10.5281/zenodo.23046366",
        "",
        f"## Books ({len(books)})",
        "",
    ]
    for book in books:
        title = clean(book.get("title")) or clean(book.get("slug"))
        lines.extend([
            f"### {title}",
            "",
            f"- Canonical page: {clean(book.get('url'))}",
            f"- Language: {clean(book.get('language'))}",
            f"- Category: {clean(book.get('category'))}",
        ])
        if clean(book.get("subtitle")):
            lines.append(f"- Subtitle: {clean(book.get('subtitle'))}")
        if clean(book.get("google_books_url")):
            lines.append(f"- Google Books: {clean(book.get('google_books_url'))}")
        if clean(book.get("preview_url")):
            lines.append(f"- Preview: {clean(book.get('preview_url'))}")
        if clean(book.get("doi")):
            lines.append(f"- DOI: {clean(book.get('doi'))}")
        lines.append("")
        summary = str(book.get("summary") or "").strip()
        if summary:
            lines.append(summary)
            lines.append("")
        elif clean(book.get("seo_description")):
            lines.append(clean(book.get("seo_description")))
            lines.append("")
        topics = [clean(x) for x in (book.get("key_topics") or []) if clean(x)]
        if topics:
            lines.append("Key topics: " + "; ".join(topics))
            lines.append("")
        learning = [clean(x) for x in (book.get("learning") or []) if clean(x)]
        if learning:
            lines.append("What readers learn:")
            lines.extend(f"- {item}" for item in learning)
            lines.append("")
        if clean(book.get("target_audience")):
            lines.append("Audience: " + clean(book.get("target_audience")))
            lines.append("")
    lines.extend([
        "## Discovery policy",
        "",
        "- Canonical HTML pages, robots.txt and XML sitemaps are authoritative.",
        "- This file is an additional convenience surface for systems that consume plain-text discovery indexes.",
        "- Crawlers with published user-agent tokens are explicitly allowed in robots.txt where useful; other standards-compliant crawlers are covered by the general User-agent: * Allow: / policy.",
        "",
    ])
    LLMS_FULL.write_text("\n".join(lines), encoding="utf-8")


def patch_llms_index() -> bool:
    if not LLMS.exists():
        return False
    text = LLMS.read_text(encoding="utf-8")
    original = text
    text = re.sub(r"\n## Extended AI discovery\n.*?(?=\n## |\Z)", "", text, flags=re.S)
    block = (
        "\n## Extended AI discovery\n\n"
        f"- Expanded full-text machine index: {SITE}/llms-full.txt\n"
        f"- Machine-readable books catalog: {BOOKS_BASE}/catalog.json\n"
        f"- Text-first HTML catalog: {BOOKS_BASE}/all-books/\n"
        f"- Search/AI crawler policy: {SITE}/robots.txt\n"
    )
    text = text.rstrip() + "\n" + block
    if text != original:
        LLMS.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    catalog = load_json(CATALOG, {})
    catalog_by_slug = {
        clean(book.get("slug")): book
        for book in (catalog.get("books", []) if isinstance(catalog, dict) else [])
        if isinstance(book, dict) and clean(book.get("slug"))
    }

    changed_heads = 0
    candidates = [ROOT / "index.html", BOOKS / "index.html", BOOKS / "all-books" / "index.html", BOOKS / "author" / "index.html", BOOKS / "topics" / "index.html"]
    candidates.extend(sorted(BOOKS.glob("*/index.html")))
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        changed_heads += int(patch_head(path))

    changed_schemas = 0
    for slug in catalog_by_slug:
        changed_schemas += int(update_book_schema(BOOKS / slug / "index.html", catalog_by_slug))

    catalog_changed = enrich_catalog(catalog)
    catalog = load_json(CATALOG, catalog)
    write_llms_full(catalog)
    llms_changed = patch_llms_index()

    print(
        "AI visibility hardening: "
        f"{changed_heads} HTML heads updated; "
        f"{changed_schemas} Book schemas linked to the canonical author/library entities; "
        f"catalog={'updated' if catalog_changed else 'unchanged'}; "
        f"llms.txt={'updated' if llms_changed else 'unchanged'}; llms-full.txt generated."
    )


if __name__ == "__main__":
    main()
