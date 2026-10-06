#!/usr/bin/env python3
"""Build a thematic books index and link every public book page to it."""

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
COMPLETED = BOOKS / "completed.json"
EXTRA = BOOKS / "source-reviewed-extra.json"
TOPICS_PAGE = BOOKS / "topics" / "index.html"
START = "<!-- topic-index-link:start -->"
END = "<!-- topic-index-link:end -->"

GROUPS = [
    ("Trading & Markets", "trading-markets", ("trading", "smart money", "wyckoff", "forex", "futures", "options trading", "market structure", "scalping", "volume profile", "macd", "liquidity", "order block", "fair value gap", "ict", "silver bullet", "turtle soup", "smt")),
    ("Artificial Intelligence & Prompt Engineering", "ai-prompt-engineering", ("artificial intelligence", "ai", "prompt", "machine learning", "generative ai", "llm", "chatgpt", "claude", "gemini", "agent", "rag")),
    ("Business, Marketing & E-Commerce", "business-marketing-ecommerce", ("business", "marketing", "e-commerce", "ecommerce", "entrepreneur", "sales", "seller", "commerce")),
    ("Turkish Language Learning", "turkish-language", ("turkish language", "turkish a1", "turkish a2", "visual grammar", "grammar book booster", "language learning")),
    ("Technology, Software & Data", "technology-software-data", ("software", "programming", "developer", "web development", "data science", "technology", "api", "coding")),
    ("Literature, Poetry & Classics", "literature-poetry-classics", ("literature", "poetry", "poem", "classic", "fiction", "novel", "shahnameh", "rumi", "hafez", "khayyam")),
    ("Mindfulness, Psychology & Personal Growth", "mindfulness-psychology-growth", ("mindfulness", "psychology", "personal growth", "self-help", "meditation", "zen", "mental", "habit", "motivation", "productivity")),
    ("Money, Economics & Financial Life", "money-economics", ("economics", "economic", "money", "poverty", "financial life", "personal finance", "wealth")),
]
FALLBACK = ("Other Books", "other-books")

CTA_COPY = {
    "en": ("Browse Books by Topic", "Explore the library by subject and find related books faster.", "Explore the Topic Index"),
    "tr": ("Kitapları Konuya Göre Keşfet", "Kütüphaneyi konu başlıklarına göre inceleyin ve ilgili kitapları daha hızlı bulun.", "Konu Dizinini Aç"),
    "de": ("Bücher nach Themen entdecken", "Durchsuchen Sie die Bibliothek nach Themen und finden Sie verwandte Bücher schneller.", "Themenindex öffnen"),
    "es": ("Explorar libros por tema", "Recorre la biblioteca por temas y encuentra más rápido libros relacionados.", "Abrir el índice temático"),
    "fr": ("Explorer les livres par thème", "Parcourez la bibliothèque par sujet et trouvez plus rapidement des livres associés.", "Ouvrir l’index thématique"),
    "fa": ("جست‌وجوی کتاب‌ها بر اساس موضوع", "کتابخانه را بر اساس موضوع مرور کنید و کتاب‌های مرتبط را سریع‌تر پیدا کنید.", "مشاهده فهرست موضوعی"),
}


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def merged_books():
    base = load_json(DATA, [])
    by_slug = {row.get("slug"): dict(row) for row in base if isinstance(row, dict) and row.get("slug")}
    for path in (COMPLETED, EXTRA):
        extra = load_json(path, {})
        if not isinstance(extra, dict):
            continue
        for slug, values in extra.items():
            if slug not in by_slug or not isinstance(values, dict):
                continue
            for key, value in values.items():
                if value not in (None, "", [], {}):
                    by_slug[slug][key] = value
    books = []
    for slug, book in by_slug.items():
        if slug in {"author", "topics"}:
            continue
        if not (BOOKS / slug / "index.html").exists():
            continue
        books.append(book)
    return books


def searchable_text(book):
    # Prefer controlled catalog metadata. Long summaries are intentionally excluded
    # because incidental words can otherwise move unrelated books into the wrong topic.
    values = [book.get("category"), book.get("title")]
    values.extend(book.get("key_topics") or [])
    return " ".join(str(v or "") for v in values).lower()


def has_term(text, term):
    # Match complete words/phrases rather than arbitrary substrings. This prevents
    # short labels such as ICT, AI, RAG or API from matching inside unrelated words.
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def classify(book):
    text = searchable_text(book)
    for label, anchor, needles in GROUPS:
        if any(has_term(text, needle) for needle in needles):
            return label, anchor
    return FALLBACK


def page_language(text):
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, re.I)
    if not match:
        return "en"
    return match.group(1).lower().split("-")[0]


def remove_existing_cta(text):
    return re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', "", text, flags=re.S)


def cta_block(lang):
    title, note, button = CTA_COPY.get(lang, CTA_COPY["en"])
    return f'''\n{START}
<section class="section topic-index-cta" aria-label="Books by topic">
  <div class="topic-index-icon" aria-hidden="true">
    <svg viewBox="0 0 48 48" focusable="false"><path d="M8 10.5h13.5c4 0 7 2 7 5.5v22c0-3.5-3-5.5-7-5.5H8v-22Z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/><path d="M40 10.5H26.5c-4 0-7 2-7 5.5v22c0-3.5 3-5.5 7-5.5H40v-22Z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/><path d="M14 17h8M14 22h8M32 17h3M32 22h3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
  </div>
  <div>
    <h2>{esc(title)}</h2>
    <p>{esc(note)}</p>
    <div class="actions"><a class="action primary" href="../topics/">{esc(button)}</a></div>
  </div>
</section>
{END}
'''


def add_cta_to_book_pages():
    updated = 0
    for path in sorted(BOOKS.glob("*/index.html")):
        if path.parent.name in {"author", "topics"}:
            continue
        text = path.read_text(encoding="utf-8")
        clean = remove_existing_cta(text)
        block = cta_block(page_language(clean))
        marker = re.search(r'</main>', clean, re.I)
        if not marker:
            continue
        rendered = clean[:marker.start()] + block + clean[marker.start():]
        if rendered != text:
            path.write_text(rendered, encoding="utf-8")
            updated += 1
    return updated


def book_card(book):
    title = book.get("title") or "Untitled"
    slug = book.get("slug") or ""
    cover = book.get("cover_url") or ""
    category = book.get("category") or "General"
    language = book.get("language") or ""
    search = " ".join(str(x or "") for x in (title, category, language, book.get("subtitle"))).lower()
    cover_html = f'<img class="topic-book-cover" src="{esc(cover)}" alt="Book cover of {esc(title)} by Faramarz Kowsari" title="{esc(title)} — book cover by Faramarz Kowsari" loading="lazy" decoding="async">' if cover else '<div class="topic-book-cover topic-book-cover-placeholder" aria-hidden="true"></div>'
    language_badge = f'<span class="topic-badge">{esc(language)}</span>' if language else ""
    return f'''<article class="topic-book-card" data-search="{esc(search)}">
  <a class="topic-cover-link" href="../{esc(slug)}/" aria-label="Open {esc(title)}">{cover_html}</a>
  <div class="topic-book-body">
    <h3><a href="../{esc(slug)}/">{esc(title)}</a></h3>
    <div class="topic-badges"><span class="topic-badge">{esc(category)}</span>{language_badge}</div>
  </div>
</article>'''


def build_topics_page(books):
    groups = {}
    for book in books:
        label, anchor = classify(book)
        groups.setdefault(label, {"anchor": anchor, "items": []})["items"].append(book)

    ordered = []
    for label, anchor, _ in GROUPS:
        if label in groups:
            ordered.append((label, anchor, groups[label]["items"]))
    if FALLBACK[0] in groups:
        ordered.append((FALLBACK[0], FALLBACK[1], groups[FALLBACK[0]]["items"]))

    chips = "\n".join(
        f'<a class="topic-chip" href="#{esc(anchor)}">{esc(label)} <span>{len(items)}</span></a>'
        for label, anchor, items in ordered
    )
    sections = []
    for label, anchor, items in ordered:
        items = sorted(items, key=lambda b: (str(b.get("title") or "").casefold(), b.get("sequence") or 0))
        cards = "\n".join(book_card(book) for book in items)
        sections.append(f'''<section class="topic-group" id="{esc(anchor)}">
  <div class="topic-group-header"><h2>{esc(label)}</h2><span class="topic-count">{len(items)} book{'s' if len(items) != 1 else ''}</span></div>
  <div class="topic-books-grid">{cards}</div>
</section>''')

    TOPICS_PAGE.parent.mkdir(parents=True, exist_ok=True)
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="author" content="Faramarz Kowsari">
<title>Books by Topic | Faramarz Kowsari</title>
<meta name="description" content="Browse books by Faramarz Kowsari by subject, including trading and markets, artificial intelligence, business, Turkish language learning, technology, literature, mindfulness and economics.">
<link rel="canonical" href="https://faramarzkowsari.github.io/books/topics/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Faramarz Kowsari Books">
<meta property="og:title" content="Books by Topic | Faramarz Kowsari">
<meta property="og:description" content="Explore the Faramarz Kowsari book catalog by subject and quickly find related titles.">
<meta property="og:url" content="https://faramarzkowsari.github.io/books/topics/">
<link rel="stylesheet" href="../styles.css">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"CollectionPage","name":"Books by Topic","url":"https://faramarzkowsari.github.io/books/topics/","author":{{"@type":"Person","name":"Faramarz Kowsari","url":"https://faramarzkowsari.github.io/books/author/"}},"description":"A thematic index of books by Faramarz Kowsari."}}</script>
</head>
<body>
<main class="book-page topics-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../">Home</a><span>›</span><a href="../">Books</a><span>›</span><span aria-current="page">Books by Topic</span></nav>
  <section class="topics-hero">
    <p class="author-kicker">Faramarz Kowsari Books</p>
    <h1>Books by Topic</h1>
    <p>Browse the catalog by subject to find related books, series and learning paths more quickly.</p>
    <div class="actions"><a class="action" href="../">All Books</a><a class="action" href="../author/">About the Author</a></div>
  </section>
  <section class="topic-search-panel" aria-label="Search topic index">
    <label for="topic-search">Search this thematic index</label>
    <input id="topic-search" type="search" placeholder="Search by title, subject or language…" autocomplete="off">
  </section>
  <nav class="topic-jump-grid" aria-label="Topics">{chips}</nav>
  <div id="topic-groups">{''.join(sections)}</div>
  <p class="topic-empty" id="topic-empty" hidden>No matching books were found in this thematic index.</p>
</main>
<script>
(function(){{
  const input = document.getElementById('topic-search');
  const cards = Array.from(document.querySelectorAll('.topic-book-card'));
  const groups = Array.from(document.querySelectorAll('.topic-group'));
  const empty = document.getElementById('topic-empty');
  function filter(){{
    const q = input.value.trim().toLowerCase();
    let visibleTotal = 0;
    cards.forEach(card => {{ const show = !q || card.dataset.search.includes(q); card.hidden = !show; if(show) visibleTotal++; }});
    groups.forEach(group => {{ const visible = group.querySelectorAll('.topic-book-card:not([hidden])').length; group.hidden = visible === 0; }});
    empty.hidden = visibleTotal !== 0;
  }}
  input.addEventListener('input', filter);
}})();
</script>
</body>
</html>'''
    TOPICS_PAGE.write_text(page, encoding="utf-8")
    return len(ordered)


def main():
    books = merged_books()
    group_count = build_topics_page(books)
    linked = add_cta_to_book_pages()
    print(f"Built thematic index with {len(books)} books across {group_count} topic groups.")
    print(f"Topic-index link added or refreshed on {linked} book pages.")


if __name__ == "__main__":
    main()
