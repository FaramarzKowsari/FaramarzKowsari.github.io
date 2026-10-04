#!/usr/bin/env python3
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
DATA = BOOKS_DIR / "books.json"
ADDITIONS_GLOB = "catalog-additions*.json"

DEFAULTS = {
    "status": "active",
    "content_status": "pending_pdf",
    "language": "English",
    "category": "",
    "translation_group": "",
    "subtitle": "",
    "description": "",
    "summary": "",
    "key_topics": [],
    "target_audience": "",
    "publisher": "",
    "published_date": "",
    "isbn": "",
    "youtube_url": "",
    "podcast_url": "",
    "slides_url": "",
    "doi": "",
    "crossref_status": "not_registered",
}


def load(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


books = load(DATA, [])
addition_paths = sorted(BOOKS_DIR.glob(ADDITIONS_GLOB))
additions = []
for addition_path in addition_paths:
    payload = load(addition_path, [])
    if not isinstance(payload, list):
        raise SystemExit(f"{addition_path} must contain a JSON array")
    additions.extend(payload)

if not isinstance(books, list):
    raise SystemExit("books/books.json must contain a JSON array")

by_id = {b.get("google_books_id"): b for b in books if b.get("google_books_id")}
by_slug = {b.get("slug"): b for b in books if b.get("slug")}
max_seq = max((int(b.get("sequence") or 0) for b in books), default=0)
added = 0
updated = 0

for raw in additions:
    if not isinstance(raw, dict):
        raise SystemExit("Every catalog addition must be a JSON object")
    item = dict(DEFAULTS)
    item.update(raw)
    gid = str(item.get("google_books_id") or "").strip()
    slug = str(item.get("slug") or "").strip()
    title = str(item.get("title") or "").strip()
    if not gid or not slug or not title:
        raise SystemExit(f"Catalog addition requires google_books_id, slug and title: {raw}")

    existing = by_id.get(gid)
    if existing:
        # Preserve source-reviewed/completed content while allowing verified catalog metadata to refresh.
        protected = {"sequence", "content_status", "summary", "key_topics", "target_audience", "seo_description", "learning", "related_ids", "source_reviewed"}
        for key, value in item.items():
            if key in protected:
                continue
            if value not in ("", None, [], {}):
                existing[key] = value
        updated += 1
        continue

    slug_owner = by_slug.get(slug)
    if slug_owner and slug_owner.get("google_books_id") != gid:
        raise SystemExit(f"Duplicate slug {slug!r} belongs to another Google Books ID")

    max_seq += 1
    item["sequence"] = max_seq
    books.append(item)
    by_id[gid] = item
    by_slug[slug] = item
    added += 1

books.sort(key=lambda b: (int(b.get("sequence") or 999999), str(b.get("title") or "").lower()))
DATA.write_text(json.dumps(books, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    f"Catalog merge: {added} added, {updated} refreshed, {len(books)} total records "
    f"from {len(addition_paths)} addition file(s)"
)
