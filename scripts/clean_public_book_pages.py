#!/usr/bin/env python3
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
COMPLETED = BOOKS / "completed.json"
EXTRA = BOOKS / "source-reviewed-extra.json"
BASE = "https://faramarzkowsari.github.io/books"
AUTHOR = "Faramarz Kowsari"

LANG_CODES = {
    "English": "en", "Türkçe": "tr", "Turkish": "tr",
    "Español": "es", "Spanish": "es", "Français": "fr",
    "French": "fr", "Deutsch": "de", "German": "de",
    "فارسی": "fa", "Persian": "fa",
}
LOCALES = {"en": "en_US", "tr": "tr_TR", "es": "es_ES", "fr": "fr_FR", "de": "de_DE", "fa": "fa_IR"}
RTL = {"fa"}

LABELS = {
    "en": {"all": "All books", "about": "About this book", "learn": "What you will learn", "topics": "Key topics", "audience": "Who this book is for", "related": "Related books", "buy": "View / Buy on Google Books", "buy_bottom": "Read / Buy on Google Books", "browse": "Browse all books"},
    "tr": {"all": "Tüm kitaplar", "about": "Kitap hakkında", "learn": "Neler öğreneceksiniz", "topics": "Temel konular", "audience": "Bu kitap kimler için?", "related": "İlgili kitaplar", "buy": "Google Books'ta İncele / Satın Al", "buy_bottom": "Google Books'ta Oku / Satın Al", "browse": "Tüm kitaplara göz at"},
    "es": {"all": "Todos los libros", "about": "Sobre este libro", "learn": "Lo que aprenderás", "topics": "Temas clave", "audience": "Para quién es este libro", "related": "Libros relacionados", "buy": "Ver / Comprar en Google Books", "buy_bottom": "Leer / Comprar en Google Books", "browse": "Ver todos los libros"},
    "fr": {"all": "Tous les livres", "about": "À propos de ce livre", "learn": "Ce que vous apprendrez", "topics": "Thèmes clés", "audience": "À qui s'adresse ce livre ?", "related": "Livres associés", "buy": "Voir / Acheter sur Google Books", "buy_bottom": "Lire / Acheter sur Google Books", "browse": "Voir tous les livres"},
    "de": {"all": "Alle Bücher", "about": "Über dieses Buch", "learn": "Was Sie lernen", "topics": "Zentrale Themen", "audience": "Für wen dieses Buch gedacht ist", "related": "Verwandte Bücher", "buy": "Auf Google Books ansehen / kaufen", "buy_bottom": "Auf Google Books lesen / kaufen", "browse": "Alle Bücher ansehen"},
    "fa": {"all": "همه کتاب‌ها", "about": "درباره این کتاب", "learn": "چه چیزهایی یاد می‌گیرید", "topics": "موضوعات کلیدی", "audience": "این کتاب برای چه کسانی است؟", "related": "کتاب‌های مرتبط", "buy": "مشاهده / خرید در Google Books", "buy_bottom": "مطالعه / خرید در Google Books", "browse": "مشاهده همه کتاب‌ها"},
}

PROCESS_MARKERS = (
    "source review status", "source-reviewed for this page", "source examined so far",
    "source material reviewed so far", "still required for full source-level analysis",
    "when their source pages are supplied", "former individual google books listings",
    "google books publication structure", "reviewed: 150 pages", "partial source review",
    "can be added here later without changing this page url", "reviewed portion",
)

A1_SLUG = "turkish-a1-visual-grammar"
A2_SLUG = "turkish-a2-visual-grammar"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def lang_code(book):
    return book.get("language_code") or LANG_CODES.get(book.get("language"), "en")


def paragraph_html(text):
    chunks = [p.strip() for p in str(text or "").split("\n\n") if p.strip()]
    return "\n".join(f"    <p>{esc(p)}</p>" for p in chunks)


def list_html(items):
    return "\n".join(f"      <li>{esc(item)}</li>" for item in (items or []) if str(item).strip())


def first_sentences(text, count=2):
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return " ".join(p for p in parts[:count] if p).strip()


def extract_meta_description(text):
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', text, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def extract_subtitle(text):
    m = re.search(r'<p\s+class=["\']subtitle["\']>(.*?)</p>', text, re.S | re.I)
    if not m:
        return ""
    return html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip()


def merge_book_data():
    books = load(DATA, [])
    completed = load(COMPLETED, {})
    extra = load(EXTRA, {})
    by_slug = {b.get("slug"): dict(b) for b in books if b.get("slug")}
    ready = set(completed) | set(extra)
    for slug in ready:
        book = by_slug.get(slug)
        if not book:
            continue
        for source in (completed.get(slug, {}), extra.get(slug, {})):
            for key, value in source.items():
                if value not in ("", None, [], {}):
                    book[key] = value
        book["status"] = "active"
    return books, by_slug, ready


def choose_related(book, by_slug, ready, by_id, limit=3):
    chosen = []
    seen = {book.get("google_books_id")}
    for gid in book.get("related_ids", []) or []:
        candidate = by_id.get(gid)
        if not candidate or candidate.get("slug") not in ready or gid in seen:
            continue
        chosen.append(candidate)
        seen.add(gid)
        if len(chosen) >= limit:
            return chosen
    category = book.get("category")
    pool = [b for b in by_slug.values() if b.get("slug") in ready and b.get("google_books_id") not in seen and b.get("category") == category and category]
    pool.sort(key=lambda b: (abs((b.get("sequence") or 0) - (book.get("sequence") or 0)), b.get("sequence") or 0))
    for candidate in pool:
        chosen.append(candidate)
        seen.add(candidate.get("google_books_id"))
        if len(chosen) >= limit:
            break
    return chosen


def render_standard_page(book, related, existing_text=""):
    code = lang_code(book)
    labels = LABELS.get(code, LABELS["en"])
    title = book.get("title") or "Untitled"
    subtitle = book.get("subtitle") or extract_subtitle(existing_text)
    seo = book.get("seo_description") or extract_meta_description(existing_text)
    summary = book.get("summary") or seo
    if not seo:
        seo = first_sentences(summary, 2)[:300]
    cover = book.get("cover_url") or ""
    google_url = book.get("google_books_url") or ""
    slug = book.get("slug") or ""
    canonical = f"{BASE}/{slug}/"
    language = book.get("language") or ""
    category = book.get("category") or ""
    published = book.get("published_date") or ""
    learning = [x for x in (book.get("learning") or []) if str(x).strip()]
    topics = [x for x in (book.get("key_topics") or []) if str(x).strip()]
    audience = book.get("target_audience") or ""
    direction = ' dir="rtl"' if code in RTL else ""

    meta_bits = [AUTHOR] + [str(x) for x in (language, category, published) if x]
    meta_line = " · ".join(meta_bits)

    schema = {"@context": "https://schema.org", "@type": "Book", "name": title, "author": {"@type": "Person", "name": AUTHOR, "url": "https://faramarzkowsari.github.io/"}, "inLanguage": code, "description": seo or summary, "url": canonical, "sameAs": google_url}
    if subtitle:
        schema["alternateName"] = subtitle
    if cover:
        schema["image"] = cover
    if published:
        schema["datePublished"] = str(published)
    if topics:
        schema["about"] = topics[:20]
    if audience:
        schema["audience"] = {"@type": "Audience", "audienceType": audience}

    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://faramarzkowsari.github.io/"},
        {"@type": "ListItem", "position": 2, "name": "Books", "item": f"{BASE}/"},
        {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
    ]}

    related_html = "\n".join(f'      <li><a href="../{esc(item["slug"])}/">{esc(item.get("title") or "Untitled")}</a></li>' for item in related)
    cover_html = f'    <img src="{esc(cover)}" alt="{esc(title)} book cover" loading="eager" decoding="async">\n' if cover else ""
    subtitle_html = f'      <p class="subtitle">{esc(subtitle)}</p>\n' if subtitle else ""
    learn_html = f'''\n  <section class="section"><h2>{esc(labels["learn"])}</h2><ul>\n{list_html(learning)}\n    </ul></section>\n''' if learning else ""
    topics_html = f'''\n  <section class="section"><h2>{esc(labels["topics"])}</h2><ul>\n{list_html(topics)}\n    </ul></section>\n''' if topics else ""
    audience_html = f'''\n  <section class="section"><h2>{esc(labels["audience"])}</h2><p>{esc(audience)}</p></section>\n''' if audience else ""
    related_section = f'''\n  <section class="section"><h2>{esc(labels["related"])}</h2><ul>\n{related_html}\n    </ul></section>\n''' if related_html else ""
    buy_top = f'<a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer">{esc(labels["buy"])}</a>' if google_url else ""
    buy_bottom = f'<a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer">{esc(labels["buy_bottom"])}</a>' if google_url else ""

    return f'''<!doctype html>
<html lang="{esc(code)}"{direction}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="author" content="{AUTHOR}">
<title>{esc(title)} | {AUTHOR}</title>
<meta name="description" content="{esc(seo or summary)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="sitemap" type="application/xml" href="../sitemap.xml">
<meta property="og:type" content="book">
<meta property="og:site_name" content="Faramarz Kowsari Books">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(seo or summary)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(cover)}">
<meta property="og:image:alt" content="Cover of {esc(title)} by {AUTHOR}">
<meta property="og:locale" content="{esc(LOCALES.get(code, 'en_US'))}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(seo or summary)}">
<meta name="twitter:image" content="{esc(cover)}">
<link rel="stylesheet" href="../styles.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>
</head>
<body{direction}>
<main class="book-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../">Home</a><span>›</span><a href="../">Books</a><span>›</span><span aria-current="page">{esc(title)}</span></nav>
  <p><a href="../">← {esc(labels["all"])}</a></p>
  <section class="book-top">
{cover_html}    <div>
      <h1>{esc(title)}</h1>
{subtitle_html}      <p class="meta">{esc(meta_line)}</p>
      <div class="actions">{buy_top}</div>
    </div>
  </section>

  <section class="section"><h2>{esc(labels["about"])}</h2>
{paragraph_html(summary)}
  </section>
{learn_html}{topics_html}{audience_html}{related_section}
  <section class="section"><div class="actions">{buy_bottom}<a class="action" href="../">{esc(labels["browse"])}</a></div></section>
</main>
</body>
</html>'''


def sanitize_custom_page(path):
    text = path.read_text(encoding="utf-8")
    original = text
    text = re.sub(r'\s*<p class="small">\s*Google Books ID:.*?</p>', '', text, flags=re.S | re.I)
    for marker in PROCESS_MARKERS:
        pattern = re.compile(r'\n?<section class="section">(?:(?!</section>).)*' + re.escape(marker) + r'(?:(?!</section>).)*</section>\n?', re.S | re.I)
        text = pattern.sub('\n', text)
    text = text.replace('source-reviewed', 'detailed').replace('Source-reviewed', 'Detailed')
    text = re.sub(r'\n{3,}', '\n\n', text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def clean_catalog(path):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    replacements = {
        'Browse source-reviewed books by Faramarz Kowsari': 'Browse books by Faramarz Kowsari',
        'A multilingual library of source-reviewed book pages with direct Google Books links.': 'A multilingual library of books by Faramarz Kowsari with direct Google Books links.',
        'AI, trading, business, technology and personal-growth books with permanent source-reviewed pages.': 'AI, trading, business, technology and personal-growth books with dedicated pages and direct Google Books links.',
        'Multilingual source-reviewed books by Faramarz Kowsari with direct Google Books links.': 'Multilingual books by Faramarz Kowsari with direct Google Books links.',
        'Every source-reviewed title below has a permanent crawlable page and a direct Google Books destination.': 'Explore the titles below by subject, language and interest, with dedicated book pages and direct Google Books destinations.',
        'Source-reviewed book pages': 'Explore the book collection',
        'crawlable book pages.': 'books.',
        'crawlable book page': 'book',
        'Source-reviewed book': 'Book',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace('source-reviewed', 'detailed').replace('Source-reviewed', 'Detailed')
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


books, by_slug, ready = merge_book_data()
by_id = {b.get("google_books_id"): b for b in by_slug.values() if b.get("google_books_id")}
standardized = 0
preserved = 0

for slug in sorted(ready):
    book = by_slug.get(slug)
    if not book:
        continue
    path = BOOKS / slug / "index.html"
    if not path.exists():
        continue
    if slug in {A1_SLUG, A2_SLUG}:
        preserved += int(sanitize_custom_page(path))
        continue
    current = path.read_text(encoding="utf-8")
    related = choose_related(book, by_slug, ready, by_id)
    rendered = render_standard_page(book, related, current)
    if rendered != current:
        path.write_text(rendered, encoding="utf-8")
        standardized += 1

clean_catalog(BOOKS / "index.html")
print(f"Applied the public sales/SEO template to {standardized} book pages in this run.")
print("Turkish A1 and A2 remain custom flagship landing pages and are sanitized for public presentation.")
