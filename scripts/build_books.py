import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
DATA = BOOKS_DIR / "books.json"
COMPLETED = BOOKS_DIR / "completed.json"
REVIEWS_DIR = BOOKS_DIR / "source_reviews"
SITE_BASE = "https://faramarzkowsari.github.io/books"
AUTHOR = "Faramarz Kowsari"

EMPTY = ("", None, [], {})
CONTROL_KEYS = {"preserve_page"}
LANG_CODES = {
    "English": "en",
    "Türkçe": "tr",
    "Turkish": "tr",
    "Español": "es",
    "Spanish": "es",
    "Français": "fr",
    "French": "fr",
    "Deutsch": "de",
    "German": "de",
    "فارسی": "fa",
    "Persian": "fa",
}


def esc(value):
    return html.escape(str(value or ""), quote=True)


def nonempty(value):
    return value not in EMPTY


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def paragraph_html(text):
    chunks = [p.strip() for p in str(text or "").split("\n\n") if p.strip()]
    return "\n".join(f"    <p>{esc(p)}</p>" for p in chunks)


def list_html(items):
    return "\n".join(f"      <li>{esc(item)}</li>" for item in items if str(item).strip())


def language_code(book):
    return book.get("language_code") or LANG_CODES.get(book.get("language"), "en")


def compact_completed_record(book):
    skip = {"sequence", "slug", "google_books_id", "google_books_url", "cover_url", "status", "language_code"}
    record = {
        key: value
        for key, value in book.items()
        if key not in skip and nonempty(value)
    }
    record["source_reviewed"] = True
    return record


books = load_json(DATA, [])
completed = load_json(COMPLETED, {})

if not isinstance(books, list):
    raise SystemExit("books/books.json must contain a JSON array")
if not isinstance(completed, dict):
    raise SystemExit("books/completed.json must contain a JSON object")

reviews = {}
review_files = sorted(REVIEWS_DIR.glob("*.json")) if REVIEWS_DIR.exists() else []
for review_file in review_files:
    payload = load_json(review_file, {})
    if not isinstance(payload, dict):
        raise SystemExit(f"{review_file} must contain a JSON object")
    overlap = set(reviews).intersection(payload)
    if overlap:
        raise SystemExit(f"Duplicate source-review IDs in {review_file}: {sorted(overlap)}")
    reviews.update(payload)

by_id = {book.get("google_books_id"): book for book in books if book.get("google_books_id")}
unknown = sorted(set(reviews).difference(by_id))
if unknown:
    raise SystemExit(f"Source reviews reference unknown Google Books IDs: {unknown}")

for gid, review in reviews.items():
    book = by_id[gid]
    for key, value in review.items():
        if key in CONTROL_KEYS:
            continue
        if nonempty(value):
            book[key] = value
    book["status"] = "active"
    book["content_status"] = "complete"

complete_slugs = set(completed)
complete_slugs.update(by_id[gid]["slug"] for gid in reviews)


def choose_related(book, limit=3):
    chosen = []
    seen = {book.get("google_books_id")}
    for gid in book.get("related_ids", []) or []:
        candidate = by_id.get(gid)
        if not candidate or candidate.get("slug") not in complete_slugs or gid in seen:
            continue
        chosen.append(candidate)
        seen.add(gid)
        if len(chosen) == limit:
            return chosen

    category = book.get("category")
    candidates = [
        b for b in books
        if b.get("google_books_id") not in seen
        and b.get("slug") in complete_slugs
        and category
        and b.get("category") == category
    ]
    candidates.sort(key=lambda b: (abs((b.get("sequence") or 0) - (book.get("sequence") or 0)), b.get("sequence") or 0))
    for candidate in candidates:
        chosen.append(candidate)
        seen.add(candidate.get("google_books_id"))
        if len(chosen) == limit:
            return chosen

    fallback = [
        b for b in books
        if b.get("google_books_id") not in seen and b.get("slug") in complete_slugs
    ]
    fallback.sort(key=lambda b: (abs((b.get("sequence") or 0) - (book.get("sequence") or 0)), b.get("sequence") or 0))
    for candidate in fallback:
        chosen.append(candidate)
        seen.add(candidate.get("google_books_id"))
        if len(chosen) == limit:
            break
    return chosen


def render_page(book):
    lang = language_code(book)
    slug = book["slug"]
    title = book.get("title") or "Untitled"
    subtitle = book.get("subtitle") or ""
    summary = book.get("summary") or ""
    seo = book.get("seo_description") or summary[:260]
    cover = book.get("cover_url") or ""
    google_url = book.get("google_books_url") or ""
    gid = book.get("google_books_id") or ""
    canonical = f"{SITE_BASE}/{slug}/"
    category = book.get("category") or ""
    language = book.get("language") or ""
    published = book.get("published_date") or ""
    doi = book.get("doi") or ""
    related = choose_related(book)
    book["related_ids"] = [item["google_books_id"] for item in related]

    schema = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": title,
        "author": {"@type": "Person", "name": AUTHOR},
        "inLanguage": lang,
        "description": seo,
        "image": cover,
        "url": canonical,
        "sameAs": google_url,
    }
    if published:
        schema["datePublished"] = published
    if doi:
        schema["identifier"] = {"@type": "PropertyValue", "propertyID": "DOI", "value": doi}

    meta_parts = [AUTHOR]
    for value in (language, category, published):
        if value:
            meta_parts.append(str(value))
    meta_line = " · ".join(meta_parts)

    related_html = "\n".join(
        f'      <li><a href="../{esc(item["slug"])}/">{esc(item.get("title") or "Untitled")}</a></li>'
        for item in related
    )
    if not related_html:
        related_html = "      <li>More source-reviewed books will be linked here as the library expands.</li>"

    media_lines = []
    if book.get("youtube_url"):
        media_lines.append(f'<a href="{esc(book["youtube_url"])}" target="_blank" rel="noopener">YouTube</a>')
    if book.get("podcast_url"):
        media_lines.append(f'<a href="{esc(book["podcast_url"])}" target="_blank" rel="noopener">Podcast</a>')
    if book.get("slides_url"):
        media_lines.append(f'<a href="{esc(book["slides_url"])}" target="_blank" rel="noopener">Slides</a>')
    if doi:
        media_lines.append(f'<a href="https://doi.org/{esc(doi)}" target="_blank" rel="noopener">DOI: {esc(doi)}</a>')
    if media_lines:
        media_html = "<p>" + " · ".join(media_lines) + "</p>"
    else:
        media_html = "<p>YouTube videos, podcast episodes, slide decks and DOI information can be added here later without changing this page URL.</p>"

    subtitle_html = f'      <p class="subtitle">{esc(subtitle)}</p>\n' if subtitle else ""
    cover_html = f'    <img src="{esc(cover)}" alt="{esc(title)} book cover">\n' if cover else ""
    learning = book.get("learning") or []
    topics = book.get("key_topics") or []

    return f'''<!doctype html>
<html lang="{esc(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<title>{esc(title)} | {AUTHOR}</title>
<meta name="description" content="{esc(seo)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="book">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(seo)}">
<meta property="og:image" content="{esc(cover)}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../styles.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head>
<body>
<main class="book-page">
  <p><a href="../">← All books</a></p>
  <section class="book-top">
{cover_html}    <div>
      <h1>{esc(title)}</h1>
{subtitle_html}      <p class="meta">{esc(meta_line)}</p>
      <div class="actions">
        <a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener">View / Buy on Google Books</a>
      </div>
      <p class="small">Google Books ID: {esc(gid)}</p>
    </div>
  </section>

  <section class="section">
    <h2>About this book</h2>
{paragraph_html(summary)}
  </section>

  <section class="section">
    <h2>What you will learn</h2>
    <ul>
{list_html(learning)}
    </ul>
  </section>

  <section class="section">
    <h2>Key topics</h2>
    <ul>
{list_html(topics)}
    </ul>
  </section>

  <section class="section">
    <h2>Who this book is for</h2>
    <p>{esc(book.get("target_audience") or "")}</p>
  </section>

  <section class="section">
    <h2>Related books</h2>
    <ul>
{related_html}
    </ul>
  </section>

  <section class="section">
    <h2>Media &amp; resources</h2>
    {media_html}
  </section>

  <section class="section">
    <div class="actions">
      <a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener">Read / Buy on Google Books</a>
    </div>
  </section>
</main>
</body>
</html>'''


for gid in reviews:
    related = choose_related(by_id[gid])
    by_id[gid]["related_ids"] = [item["google_books_id"] for item in related]

preserved_pages = 0
for gid, review in reviews.items():
    book = by_id[gid]
    completed[book["slug"]] = compact_completed_record(book)
    if review.get("preserve_page"):
        preserved_pages += 1
        continue
    output_dir = BOOKS_DIR / book["slug"]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(render_page(book), encoding="utf-8")

DATA.write_text(json.dumps(books, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
COMPLETED.write_text(json.dumps(completed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(f"Loaded {len(books)} book records")
print(f"Loaded {len(reviews)} source-reviewed Library records from {len(review_files)} files")
print(f"Published/updated {len(reviews) - preserved_pages} generated book pages")
print(f"Preserved {preserved_pages} custom editorial pages")
print(f"completed.json now contains {len(completed)} source-reviewed/live entries")
