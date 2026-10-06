#!/usr/bin/env python3
"""Generate separate Russian-language discovery pages for every public non-Russian book.

The original book pages remain in their source language. Russian pages live at:
    /books/<slug>/ru/
and clearly disclose the actual language of the book. The generator also:
- adds reciprocal hreflang links to original pages,
- builds /books/ru/ as a Russian catalog,
- builds /books/sitemap-ru.xml,
- supports optional hand-edited overrides in books/localizations/ru.json.
"""

import html
import json
import pathlib
import re
from xml.sax.saxutils import escape as xml_escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
OVERRIDES = BOOKS / "localizations" / "ru.json"
SITE = "https://faramarzkowsari.github.io"
BOOKS_BASE = f"{SITE}/books"
AUTHOR = "Faramarz Kowsari"

LANG_CODES = {
    "English": "en", "Türkçe": "tr", "Turkish": "tr",
    "Español": "es", "Spanish": "es", "Français": "fr", "French": "fr",
    "Deutsch": "de", "German": "de", "فارسی": "fa", "Persian": "fa",
    "Português": "pt", "Portuguese": "pt", "Português (Brasil)": "pt-BR",
    "Romanian": "ro", "Română": "ro", "Indonesian": "id", "Bahasa Indonesia": "id",
    "Filipino": "fil", "Русский": "ru", "Russian": "ru",
}

LANG_RU = {
    "en": "английском языке", "tr": "турецком языке", "es": "испанском языке",
    "fr": "французском языке", "de": "немецком языке", "fa": "персидском языке",
    "pt": "португальском языке", "pt-BR": "бразильском португальском языке",
    "ro": "румынском языке", "id": "индонезийском языке", "fil": "филиппинском языке",
    "ru": "русском языке",
}

CATEGORY_RULES = [
    (("trading", "market", "forex", "crypto", "options"),
     "трейдинг и финансовые рынки",
     "Материал помогает систематизировать рыночные понятия, логику принятия решений, управление риском и практическое применение торговой методики."),
    (("finance", "money", "financial", "econom"),
     "личные финансы и экономика",
     "Книга рассматривает финансовые решения, поведение, риски и практические способы более осознанной работы с деньгами и экономическими ограничениями."),
    (("artificial intelligence", "ai ", "ai&", "prompt", "chatgpt", "agent"),
     "искусственный интеллект",
     "Книга посвящена практическому применению искусственного интеллекта, работе с современными AI-инструментами и превращению идей в воспроизводимые рабочие процессы."),
    (("machine learning", "data science", "sql", "python", "data analysis", "analytics"),
     "анализ данных и машинное обучение",
     "Материал объясняет ключевые идеи анализа данных и машинного обучения с упором на понятные концепции, практические задачи и воспроизводимый процесс решения проблем."),
    (("business", "e-commerce", "marketing", "sales", "entrepreneur"),
     "бизнес, маркетинг и предпринимательство",
     "Книга ориентирована на практические бизнес-задачи: стратегию, маркетинг, продажи, операции, принятие решений и создание более устойчивых рабочих процессов."),
    (("psychology", "mindfulness", "personal development", "self", "relationship"),
     "психология и личное развитие",
     "Книга помогает структурировать идеи о поведении, отношениях, внимании, личных решениях и развитии, превращая общие темы в практические наблюдения и действия."),
    (("language", "turkish", "grammar", "english"),
     "изучение языков",
     "Материал создан для последовательного изучения языка и сочетает понятные объяснения, примеры и практическое закрепление навыков."),
    (("weather", "heat", "air quality", "earthquake", "disaster", "survival"),
     "безопасность, климат и устойчивость",
     "Книга собирает практические знания, которые помогают лучше понимать риски, подготовку, повседневную безопасность и принятие решений в сложных условиях."),
]

DEFAULT_CATEGORY_RU = "практическое образование и развитие навыков"
DEFAULT_PROFILE = (
    "Книга представляет тему в структурированном и прикладном формате, помогая читателю быстро понять ключевые идеи, терминологию и практическое значение материала."
)

STYLE = """
:root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.65;background:#f5f7fb;color:#172033}a{color:#1259c3}main{max-width:1040px;margin:auto;padding:28px 20px 64px}.crumbs{font-size:.95rem;margin-bottom:22px}.hero{display:grid;grid-template-columns:minmax(180px,260px) 1fr;gap:32px;align-items:start;background:#fff;border:1px solid #dfe5ef;border-radius:20px;padding:24px;box-shadow:0 12px 34px rgba(24,40,72,.08)}.hero img{width:100%;border-radius:12px;box-shadow:0 8px 22px rgba(0,0,0,.16)}h1{line-height:1.18;margin:.1em 0 .4em;font-size:clamp(2rem,5vw,3.4rem)}h2{margin-top:0}.subtitle{font-size:1.08rem;color:#4d5b70}.badge{display:inline-block;background:#eef4ff;color:#154b94;border-radius:999px;padding:6px 11px;margin:3px 5px 3px 0;font-size:.9rem}.notice{background:#fff6dc;border:1px solid #edd28a;border-radius:12px;padding:12px 14px;margin:16px 0}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.btn{display:inline-block;padding:11px 15px;border-radius:10px;text-decoration:none;font-weight:700;border:1px solid #cbd5e3;background:#fff}.btn.primary{background:#1557b0;color:#fff;border-color:#1557b0}.section{background:#fff;border:1px solid #dfe5ef;border-radius:16px;padding:22px;margin-top:20px}.topics{display:flex;flex-wrap:wrap;gap:8px}.topic{padding:7px 10px;background:#f2f5f9;border-radius:9px}.small{font-size:.92rem;color:#607086}.catalog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}.card{background:#fff;border:1px solid #dfe5ef;border-radius:15px;padding:15px}.card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:9px}.card h2{font-size:1.08rem;margin:.7rem 0 .35rem}.card a{text-decoration:none}@media(max-width:720px){.hero{grid-template-columns:1fr}.hero img{max-width:240px;margin:auto}}@media(prefers-color-scheme:dark){body{background:#111827;color:#e5e7eb}.hero,.section,.card,.btn{background:#182233;border-color:#334155}.subtitle,.small{color:#b7c2d1}.badge,.topic{background:#26364d;color:#dbeafe}.notice{background:#3d3114;border-color:#756129}}
""".strip()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def esc(v):
    return html.escape(str(v or ""), quote=True)


def lang_code(book):
    return book.get("language_code") or LANG_CODES.get(book.get("language"), "en")


def category_profile(book):
    hay = " ".join([str(book.get("category") or ""), str(book.get("title") or ""), str(book.get("subtitle") or "")]).lower()
    for needles, label, profile in CATEGORY_RULES:
        if any(n in hay for n in needles):
            return label, profile
    return DEFAULT_CATEGORY_RU, DEFAULT_PROFILE


def russian_meta(book, override):
    title = book.get("title") or "Untitled"
    source_lang = lang_code(book)
    source_lang_ru = LANG_RU.get(source_lang, "исходном языке")
    cat_ru, profile = category_profile(book)
    subtitle = book.get("subtitle") or ""
    summary_ru = override.get("summary_ru") or (
        f"«{title}» — книга Фарамарза Коусари в области «{cat_ru}». "
        f"Эта русскоязычная страница позволяет познакомиться с содержанием, ключевыми темами и практической направленностью издания перед переходом к официальной странице Google Books. "
        f"Само издание опубликовано на {source_lang_ru}."
    )
    if subtitle and not override.get("summary_ru"):
        summary_ru += f" Оригинальный подзаголовок книги: «{subtitle}»."
    seo_ru = override.get("seo_description_ru") or (
        f"{title} — описание книги на русском языке, основные темы, аудитория, бесплатный просмотр и официальная ссылка Google Books. Книга издана на {source_lang_ru}."
    )
    audience_ru = override.get("target_audience_ru") or (
        f"Для русскоязычных читателей, которым интересны {cat_ru} и которые готовы читать профессиональную литературу на {source_lang_ru}."
    )
    learning_ru = override.get("learning_ru") or [
        "быстро понять назначение книги и её практическую направленность;",
        "ознакомиться с ключевыми темами до покупки или чтения;",
        "перейти к официальной странице Google Books и доступному предварительному просмотру;",
        "сразу увидеть реальный язык издания и избежать путаницы между языком этой страницы и языком самой книги."
    ]
    return {
        "title_ru": override.get("title_ru") or title,
        "category_ru": override.get("category_ru") or cat_ru,
        "profile_ru": override.get("profile_ru") or profile,
        "summary_ru": summary_ru,
        "seo_ru": seo_ru,
        "audience_ru": audience_ru,
        "learning_ru": learning_ru,
        "source_lang": source_lang,
        "source_lang_ru": source_lang_ru,
    }


def patch_hreflang(original_path, source_lang, original_url, ru_url):
    if not original_path.exists():
        return False
    text = original_path.read_text(encoding="utf-8")
    block = (
        "<!-- russian-localization:start -->\n"
        f'<link rel="alternate" hreflang="{esc(source_lang)}" href="{esc(original_url)}">\n'
        f'<link rel="alternate" hreflang="ru" href="{esc(ru_url)}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{esc(original_url)}">\n'
        "<!-- russian-localization:end -->"
    )
    pattern = re.compile(r"\n?<!-- russian-localization:start -->.*?<!-- russian-localization:end -->", re.S)
    if pattern.search(text):
        new = pattern.sub("\n" + block, text, count=1)
    elif "</head>" in text:
        new = text.replace("</head>", block + "\n</head>", 1)
    else:
        return False
    if new != text:
        original_path.write_text(new, encoding="utf-8")
        return True
    return False


def render_book(book, meta):
    slug = book["slug"]
    original = f"{BOOKS_BASE}/{slug}/"
    canonical = f"{original}ru/"
    google = book.get("google_books_url") or ""
    gid = book.get("google_books_id") or ""
    preview = f"https://play.google.com/books/reader?id={gid}&hl=ru" if gid else ""
    cover = book.get("cover_url") or ""
    title = book.get("title") or "Untitled"
    subtitle = book.get("subtitle") or ""
    topics = [str(x).strip() for x in (book.get("key_topics") or []) if str(x).strip()]
    keywords = ", ".join([title, meta["category_ru"], "книга", "Faramarz Kowsari"] + topics[:10])

    web_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": f"{title} — описание на русском",
        "description": meta["seo_ru"],
        "inLanguage": "ru",
        "isPartOf": {"@type": "CollectionPage", "@id": f"{BOOKS_BASE}/#collection", "url": f"{BOOKS_BASE}/"},
        "mainEntity": {
            "@type": "Book",
            "@id": original + "#book",
            "name": title,
            "author": {"@type": "Person", "@id": f"{SITE}/#person", "name": AUTHOR},
            "inLanguage": meta["source_lang"],
            "url": original,
            "sameAs": google,
            "image": cover,
        },
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Books", "item": f"{BOOKS_BASE}/"},
            {"@type": "ListItem", "position": 2, "name": "Книги на русском", "item": f"{BOOKS_BASE}/ru/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
        ],
    }
    topics_html = "\n".join(f'<span class="topic" lang="en">{esc(t)}</span>' for t in topics) or '<span class="topic">Темы будут дополнены</span>'
    learn_html = "\n".join(f"<li>{esc(x)}</li>" for x in meta["learning_ru"])
    cover_html = f'<img src="{esc(cover)}" alt="Обложка книги {esc(title)}" loading="eager">' if cover else ""
    subtitle_html = f'<p class="subtitle" lang="{esc(meta["source_lang"])}">{esc(subtitle)}</p>' if subtitle else ""
    buy = f'<a class="btn primary" href="{esc(google)}" target="_blank" rel="noopener">Открыть в Google Books</a>' if google else ""
    prev = f'<a class="btn" href="{esc(preview)}" target="_blank" rel="noopener">Бесплатный просмотр</a>' if preview else ""

    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<title>{esc(title)} — описание на русском | {AUTHOR}</title>
<meta name="description" content="{esc(meta['seo_ru'])}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" hreflang="{esc(meta['source_lang'])}" href="{esc(original)}">
<link rel="alternate" hreflang="ru" href="{esc(canonical)}">
<link rel="alternate" hreflang="x-default" href="{esc(original)}">
<link rel="alternate" type="application/json" href="{BOOKS_BASE}/catalog.json" title="Machine-readable books catalog">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{esc(title)} — описание на русском">
<meta property="og:description" content="{esc(meta['seo_ru'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(cover)}">
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
<script type="application/ld+json">{json.dumps(web_schema, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>
</head>
<body>
<main>
<nav class="crumbs" aria-label="Хлебные крошки"><a href="{BOOKS_BASE}/">Все книги</a> · <a href="{BOOKS_BASE}/ru/">Русский каталог</a> · {esc(title)}</nav>
<section class="hero">
{cover_html}
<div>
<span class="badge">Русскоязычное описание</span><span class="badge">{esc(meta['category_ru'])}</span>
<h1 lang="{esc(meta['source_lang'])}">{esc(title)}</h1>
{subtitle_html}
<div class="notice"><strong>Важно:</strong> эта страница написана по-русски, но сама книга опубликована на <strong>{esc(meta['source_lang_ru'])}</strong>.</div>
<p>{esc(meta['summary_ru'])}</p>
<div class="actions">{buy}{prev}<a class="btn" href="{esc(original)}">Официальная страница книги</a></div>
</div>
</section>
<section class="section"><h2>О книге</h2><p>{esc(meta['profile_ru'])}</p><p>Автор: <strong>Faramarz Kowsari</strong>. Категория: <strong>{esc(meta['category_ru'])}</strong>.</p></section>
<section class="section"><h2>Что вы сможете узнать до покупки</h2><ul>{learn_html}</ul></section>
<section class="section"><h2>Ключевые темы</h2><p class="small">Ниже сохранена оригинальная профессиональная терминология книги.</p><div class="topics">{topics_html}</div></section>
<section class="section"><h2>Кому подойдет эта книга</h2><p>{esc(meta['audience_ru'])}</p></section>
<section class="section"><h2>Читать и купить</h2><p>Перейдите на официальную страницу Google Books, чтобы проверить доступность книги, цену и условия покупки в вашей стране. Если для книги доступен предварительный просмотр, его можно открыть отдельно.</p><div class="actions">{buy}{prev}</div></section>
</main>
</body>
</html>'''


def render_catalog(items):
    cards = []
    for book, meta in items:
        slug = book["slug"]
        title = book.get("title") or "Untitled"
        cover = book.get("cover_url") or ""
        img = f'<img src="{esc(cover)}" alt="Обложка книги {esc(title)}" loading="lazy">' if cover else ""
        cards.append(
            f'<article class="card">{img}<h2 lang="{esc(meta["source_lang"])}"><a href="../{esc(slug)}/ru/">{esc(title)}</a></h2>'
            f'<p><span class="badge">{esc(meta["category_ru"])}</span></p>'
            f'<p class="small">Книга издана на {esc(meta["source_lang_ru"])}.</p>'
            f'<p><a href="../{esc(slug)}/ru/">Описание на русском →</a></p></article>'
        )
    collection_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{BOOKS_BASE}/ru/#collection",
        "url": f"{BOOKS_BASE}/ru/",
        "name": "Книги Faramarz Kowsari — описания на русском",
        "description": "Русскоязычный каталог официальных страниц книг Faramarz Kowsari с указанием реального языка каждого издания и ссылками на Google Books.",
        "inLanguage": "ru",
        "isPartOf": {"@id": f"{BOOKS_BASE}/#collection"},
    }
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<title>Книги Faramarz Kowsari — описания на русском</title>
<meta name="description" content="Русскоязычный каталог книг Faramarz Kowsari: краткие описания, ключевые темы, язык издания, бесплатные просмотры и официальные ссылки Google Books.">
<link rel="canonical" href="{BOOKS_BASE}/ru/"><link rel="alternate" hreflang="ru" href="{BOOKS_BASE}/ru/"><link rel="alternate" hreflang="x-default" href="{BOOKS_BASE}/">
<style>{STYLE}</style><script type="application/ld+json">{json.dumps(collection_schema, ensure_ascii=False)}</script></head>
<body><main><nav class="crumbs"><a href="{BOOKS_BASE}/">← Все книги / All books</a></nav><h1>Книги Faramarz Kowsari — описания на русском</h1>
<p>Здесь собраны отдельные русскоязычные страницы книг. Они помогают русскоязычным читателям понять тему и назначение каждой книги, при этом язык самого издания всегда указан отдельно и не подменяется языком страницы.</p>
<div class="notice"><strong>Важно:</strong> большинство книг в этом каталоге изданы не на русском языке. На каждой странице это указано до перехода в Google Books.</div>
<section class="catalog-grid">{''.join(cards)}</section></main></body></html>'''


def write_sitemap(urls):
    body = "\n".join(f"  <url><loc>{xml_escape(u)}</loc></url>" for u in urls)
    (BOOKS / "sitemap-ru.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '\n</urlset>\n',
        encoding="utf-8",
    )


def main():
    books = load_json(DATA, [])
    overrides = load_json(OVERRIDES, {})
    if not isinstance(books, list):
        raise SystemExit("books/books.json must contain an array")
    if not isinstance(overrides, dict):
        overrides = {}

    generated = []
    patched = 0
    for book in books:
        slug = str(book.get("slug") or "").strip("/")
        if not slug or book.get("status") != "active":
            continue
        original_path = BOOKS / slug / "index.html"
        if not original_path.exists():
            continue
        if lang_code(book) == "ru":
            continue
        meta = russian_meta(book, overrides.get(slug, {}) if isinstance(overrides.get(slug, {}), dict) else {})
        original_url = f"{BOOKS_BASE}/{slug}/"
        ru_url = f"{original_url}ru/"
        outdir = BOOKS / slug / "ru"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "index.html").write_text(render_book(book, meta), encoding="utf-8")
        if patch_hreflang(original_path, meta["source_lang"], original_url, ru_url):
            patched += 1
        generated.append((book, meta))

    catalog_dir = BOOKS / "ru"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    generated.sort(key=lambda pair: (pair[0].get("sequence") or 999999, pair[0].get("title") or ""))
    (catalog_dir / "index.html").write_text(render_catalog(generated), encoding="utf-8")
    sitemap_urls = [f"{BOOKS_BASE}/ru/"] + [f"{BOOKS_BASE}/{book['slug']}/ru/" for book, _ in generated]
    write_sitemap(sitemap_urls)
    print(f"Russian discovery pages: {len(generated)} generated; {patched} original pages updated with hreflang; sitemap URLs: {len(sitemap_urls)}")


if __name__ == "__main__":
    main()
