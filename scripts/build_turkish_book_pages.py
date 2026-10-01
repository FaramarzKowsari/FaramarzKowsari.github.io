#!/usr/bin/env python3
"""Generate separate Turkish-language discovery pages for the public book library.

For books whose original language is not Turkish, discovery pages live at:
    /books/<slug>/tr/

Books already published in Turkish keep their original page as the Turkish page;
no duplicate /tr/ page is created for them. The generator also:
- adds Turkish hreflang alternates to original pages,
- adds Turkish hreflang alternates to Russian landing pages when present,
- builds /books/tr/ as a Turkish catalog for the whole active library,
- builds /books/sitemap-tr.xml,
- supports optional hand-edited overrides in books/localizations/tr.json.
"""

import html
import json
import pathlib
import re
from xml.sax.saxutils import escape as xml_escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
OVERRIDES = BOOKS / "localizations" / "tr.json"
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

LANG_TR = {
    "en": "İngilizce", "tr": "Türkçe", "es": "İspanyolca", "fr": "Fransızca",
    "de": "Almanca", "fa": "Farsça", "pt": "Portekizce", "pt-BR": "Brezilya Portekizcesi",
    "ro": "Romence", "id": "Endonezce", "fil": "Filipince", "ru": "Rusça",
}

CATEGORY_RULES = [
    (("artificial intelligence", " ai ", "ai&", "ai-", "prompt", "chatgpt", "claude", "agent", "llm"),
     "yapay zekâ",
     "Kitap, yapay zekânın pratik kullanımına, modern AI araçlarına ve fikirleri tekrarlanabilir iş akışlarına dönüştürmeye odaklanır."),
    (("machine learning", "data science", "sql", "python", "data analysis", "analytics", "decision tree"),
     "veri bilimi ve makine öğrenmesi",
     "İçerik; veri analizi ve makine öğrenmesinin temel kavramlarını anlaşılır açıklamalar, pratik problemler ve uygulanabilir yöntemlerle ele alır."),
    (("trading", "forex", "crypto", "options", "order block", "liquidity", "wyckoff", "macd", "smc", "market structure", "financial market"),
     "trading ve finansal piyasalar",
     "Materyal; piyasa kavramlarını, karar verme mantığını, risk yönetimini ve trading yöntemlerinin pratik uygulanmasını sistematik biçimde ele alır."),
    (("finance", "money", "financial", "econom", "installment", "poverty", "debt"),
     "kişisel finans ve ekonomi",
     "Kitap; finansal kararları, davranışları, riskleri ve para ile ekonomik kısıtlar konusunda daha bilinçli hareket etmeye yardımcı olan pratik yaklaşımları inceler."),
    (("business", "e-commerce", "marketing", "sales", "entrepreneur", "small business", "social media"),
     "işletme, pazarlama ve girişimcilik",
     "Kitap; strateji, pazarlama, satış, operasyonlar, karar verme ve daha sürdürülebilir iş süreçleri gibi pratik işletme konularına odaklanır."),
    (("psychology", "mindfulness", "personal development", "relationship", "mind", "love", "infidelity"),
     "psikoloji ve kişisel gelişim",
     "Kitap; davranış, ilişkiler, dikkat, kişisel kararlar ve gelişim konularını yapılandırarak genel fikirleri uygulanabilir gözlem ve eylemlere dönüştürür."),
    (("language", "turkish", "grammar", "english", "vocabulary"),
     "dil öğrenimi",
     "Materyal; dili adım adım öğrenmeye yardımcı olacak açıklamalar, örnekler ve becerileri pekiştiren pratiklerle hazırlanmıştır."),
    (("weather", "heat", "air quality", "earthquake", "disaster", "survival"),
     "güvenlik, iklim ve dayanıklılık",
     "Kitap; riskleri, hazırlığı, günlük güvenliği ve zor koşullarda karar vermeyi daha iyi anlamaya yardımcı olan pratik bilgileri bir araya getirir."),
]

DEFAULT_CATEGORY_TR = "uygulamalı eğitim ve beceri geliştirme"
DEFAULT_PROFILE = (
    "Kitap, konuyu yapılandırılmış ve uygulamaya dönük bir biçimde sunarak okuyucunun temel fikirleri, terminolojiyi ve içeriğin pratik değerini hızlıca anlamasına yardımcı olur."
)

STYLE = """
:root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.65;background:#f5f7fb;color:#172033}a{color:#1259c3}main{max-width:1040px;margin:auto;padding:28px 20px 64px}.crumbs{font-size:.95rem;margin-bottom:22px}.hero{display:grid;grid-template-columns:minmax(180px,260px) 1fr;gap:32px;align-items:start;background:#fff;border:1px solid #dfe5ef;border-radius:20px;padding:24px;box-shadow:0 12px 34px rgba(24,40,72,.08)}.hero img{width:100%;border-radius:12px;box-shadow:0 8px 22px rgba(0,0,0,.16)}h1{line-height:1.18;margin:.1em 0 .4em;font-size:clamp(2rem,5vw,3.4rem)}h2{margin-top:0}.subtitle{font-size:1.08rem;color:#4d5b70}.badge{display:inline-block;background:#eef4ff;color:#154b94;border-radius:999px;padding:6px 11px;margin:3px 5px 3px 0;font-size:.9rem}.notice{background:#fff6dc;border:1px solid #edd28a;border-radius:12px;padding:12px 14px;margin:16px 0}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.btn{display:inline-block;padding:11px 15px;border-radius:10px;text-decoration:none;font-weight:700;border:1px solid #cbd5e3;background:#fff}.btn.primary{background:#1557b0;color:#fff;border-color:#1557b0}.section{background:#fff;border:1px solid #dfe5ef;border-radius:16px;padding:22px;margin-top:20px}.topics{display:flex;flex-wrap:wrap;gap:8px}.topic{padding:7px 10px;background:#f2f5f9;border-radius:9px}.small{font-size:.92rem;color:#607086}.catalog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}.card{background:#fff;border:1px solid #dfe5ef;border-radius:15px;padding:15px}.card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:9px}.card h2{font-size:1.08rem;margin:.7rem 0 .35rem}.card a{text-decoration:none}@media(max-width:720px){.hero{grid-template-columns:1fr}.hero img{max-width:240px;margin:auto}}@media(prefers-color-scheme:dark){body{background:#111827;color:#e5e7eb}.hero,.section,.card,.btn{background:#182233;border-color:#334155}.subtitle,.small{color:#b7c2d1}.badge,.topic{background:#26364d;color:#dbeafe}.notice{background:#3d3114;border-color:#756129}}
""".strip()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def lang_code(book):
    return book.get("language_code") or LANG_CODES.get(book.get("language"), "en")


def category_profile(book):
    hay = " " + " ".join([
        str(book.get("category") or ""),
        str(book.get("title") or ""),
        str(book.get("subtitle") or ""),
        " ".join(str(x) for x in (book.get("key_topics") or [])[:8]),
    ]).lower() + " "
    for needles, label, profile in CATEGORY_RULES:
        if any(n in hay for n in needles):
            return label, profile
    return DEFAULT_CATEGORY_TR, DEFAULT_PROFILE


def turkish_meta(book, override):
    title = book.get("title") or "Untitled"
    source_lang = lang_code(book)
    source_lang_tr = LANG_TR.get(source_lang, "orijinal dil")
    category_tr, profile = category_profile(book)
    subtitle = book.get("subtitle") or ""
    summary_tr = override.get("summary_tr") or (
        f"“{title}”, Faramarz Kowsari'nin {category_tr} alanındaki kitaplarından biridir. "
        "Bu Türkçe tanıtım sayfası, Google Books'taki resmi sayfaya geçmeden önce kitabın amacı, temel konuları ve pratik yönü hakkında hızlı bir genel bakış sunar. "
        f"Kitabın yayın dili {source_lang_tr}."
    )
    if subtitle and not override.get("summary_tr"):
        summary_tr += f" Kitabın orijinal alt başlığı: “{subtitle}”."
    seo_tr = override.get("seo_description_tr") or (
        f"{title}: Türkçe kitap tanıtımı, temel konular, hedef okuyucu, ücretsiz önizleme ve resmi Google Books bağlantısı. Kitabın yayın dili {source_lang_tr}."
    )
    audience_tr = override.get("target_audience_tr") or (
        f"{category_tr} ile ilgilenen ve {source_lang_tr} profesyonel içerik okuyabilen Türkçe konuşan okuyucular için hazırlanmıştır."
    )
    learning_tr = override.get("learning_tr") or [
        "kitabın amacını ve pratik yönünü hızlıca anlamak;",
        "satın almadan veya okumaya başlamadan önce temel konuları görmek;",
        "resmi Google Books sayfasına ve varsa ücretsiz önizlemeye ulaşmak;",
        "bu Türkçe tanıtım sayfasının dili ile kitabın gerçek yayın dilini açıkça ayırt etmek."
    ]
    return {
        "title_tr": override.get("title_tr") or title,
        "category_tr": override.get("category_tr") or category_tr,
        "profile_tr": override.get("profile_tr") or profile,
        "summary_tr": summary_tr,
        "seo_tr": seo_tr,
        "audience_tr": audience_tr,
        "learning_tr": learning_tr,
        "source_lang": source_lang,
        "source_lang_tr": source_lang_tr,
    }


def upsert_turkish_alternate(path, tr_url):
    """Add/update one Turkish hreflang marker without disturbing other language blocks."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    block = (
        "<!-- turkish-localization:start -->\n"
        f'<link rel="alternate" hreflang="tr" href="{esc(tr_url)}">\n'
        "<!-- turkish-localization:end -->"
    )
    pattern = re.compile(r"\n?<!-- turkish-localization:start -->.*?<!-- turkish-localization:end -->", re.S)
    if pattern.search(text):
        new = pattern.sub("\n" + block, text, count=1)
    elif "</head>" in text:
        new = text.replace("</head>", block + "\n</head>", 1)
    else:
        return False
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def render_book(book, meta):
    slug = book["slug"]
    original = f"{BOOKS_BASE}/{slug}/"
    canonical = f"{original}tr/"
    ru_url = f"{original}ru/" if (BOOKS / slug / "ru" / "index.html").exists() else ""
    google = book.get("google_books_url") or ""
    gid = book.get("google_books_id") or ""
    preview = f"https://play.google.com/books/reader?id={gid}&hl=tr" if gid else ""
    cover = book.get("cover_url") or ""
    title = book.get("title") or "Untitled"
    subtitle = book.get("subtitle") or ""
    topics = [str(x).strip() for x in (book.get("key_topics") or []) if str(x).strip()]
    keywords = ", ".join([title, meta["category_tr"], "kitap", "Faramarz Kowsari"] + topics[:10])

    web_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": f"{title} — Türkçe kitap tanıtımı",
        "description": meta["seo_tr"],
        "inLanguage": "tr",
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
            {"@type": "ListItem", "position": 1, "name": "Kitaplar", "item": f"{BOOKS_BASE}/"},
            {"@type": "ListItem", "position": 2, "name": "Türkçe katalog", "item": f"{BOOKS_BASE}/tr/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
        ],
    }
    alternate_ru = f'<link rel="alternate" hreflang="ru" href="{esc(ru_url)}">\n' if ru_url else ""
    topics_html = "\n".join(f'<span class="topic" lang="en">{esc(t)}</span>' for t in topics) or '<span class="topic">Konular daha sonra ayrıntılandırılacaktır</span>'
    learn_html = "\n".join(f"<li>{esc(x)}</li>" for x in meta["learning_tr"])
    cover_html = f'<img src="{esc(cover)}" alt="{esc(title)} kitap kapağı" loading="eager">' if cover else ""
    subtitle_html = f'<p class="subtitle" lang="{esc(meta["source_lang"])}">{esc(subtitle)}</p>' if subtitle else ""
    buy = f'<a class="btn primary" href="{esc(google)}" target="_blank" rel="noopener">Google Books\'ta aç</a>' if google else ""
    prev = f'<a class="btn" href="{esc(preview)}" target="_blank" rel="noopener">Ücretsiz önizleme</a>' if preview else ""

    return f'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<title>{esc(title)} — Türkçe kitap tanıtımı | {AUTHOR}</title>
<meta name="description" content="{esc(meta['seo_tr'])}">
<meta name="keywords" content="{esc(keywords)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" hreflang="{esc(meta['source_lang'])}" href="{esc(original)}">
<link rel="alternate" hreflang="tr" href="{esc(canonical)}">
{alternate_ru}<link rel="alternate" hreflang="x-default" href="{esc(original)}">
<link rel="alternate" type="application/json" href="{BOOKS_BASE}/catalog.json" title="Machine-readable books catalog">
<meta property="og:type" content="website">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{esc(title)} — Türkçe kitap tanıtımı">
<meta property="og:description" content="{esc(meta['seo_tr'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(cover)}">
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
<script type="application/ld+json">{json.dumps(web_schema, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>
</head>
<body>
<main>
<nav class="crumbs" aria-label="İçerik yolu"><a href="{BOOKS_BASE}/">Tüm kitaplar</a> · <a href="{BOOKS_BASE}/tr/">Türkçe katalog</a> · {esc(title)}</nav>
<section class="hero">
{cover_html}
<div>
<span class="badge">Türkçe tanıtım</span><span class="badge">{esc(meta['category_tr'])}</span>
<h1 lang="{esc(meta['source_lang'])}">{esc(title)}</h1>
{subtitle_html}
<div class="notice"><strong>Önemli:</strong> bu tanıtım sayfası Türkçedir; kitabın kendisi <strong>{esc(meta['source_lang_tr'])}</strong> yayımlanmıştır.</div>
<p>{esc(meta['summary_tr'])}</p>
<div class="actions">{buy}{prev}<a class="btn" href="{esc(original)}">Kitabın resmi sayfası</a></div>
</div>
</section>
<section class="section"><h2>Kitap hakkında</h2><p>{esc(meta['profile_tr'])}</p><p>Yazar: <strong>Faramarz Kowsari</strong>. Kategori: <strong>{esc(meta['category_tr'])}</strong>.</p></section>
<section class="section"><h2>Satın almadan önce neleri görebilirsiniz?</h2><ul>{learn_html}</ul></section>
<section class="section"><h2>Temel konular</h2><p class="small">Aşağıda kitabın özgün profesyonel terminolojisi korunmuştur.</p><div class="topics">{topics_html}</div></section>
<section class="section"><h2>Bu kitap kimler için?</h2><p>{esc(meta['audience_tr'])}</p></section>
<section class="section"><h2>Oku ve satın al</h2><p>Kitabın ülkenizdeki erişilebilirliğini, fiyatını ve satın alma koşullarını kontrol etmek için resmi Google Books sayfasını açın. Önizleme sunuluyorsa ayrı bağlantıdan ücretsiz olarak görüntüleyebilirsiniz.</p><div class="actions">{buy}{prev}</div></section>
</main>
</body>
</html>'''


def render_catalog(items):
    cards = []
    for book, meta, target_url in items:
        title = book.get("title") or "Untitled"
        cover = book.get("cover_url") or ""
        source_is_tr = meta["source_lang"] == "tr"
        img = f'<img src="{esc(cover)}" alt="{esc(title)} kitap kapağı" loading="lazy">' if cover else ""
        note = "Kitap Türkçe yayımlanmıştır." if source_is_tr else f"Kitabın yayın dili: {esc(meta['source_lang_tr'])}."
        action = "Kitap sayfasına git →" if source_is_tr else "Türkçe tanıtımı aç →"
        cards.append(
            f'<article class="card">{img}<h2 lang="{esc(meta["source_lang"])}"><a href="{esc(target_url)}">{esc(title)}</a></h2>'
            f'<p><span class="badge">{esc(meta["category_tr"])}</span></p>'
            f'<p class="small">{note}</p>'
            f'<p><a href="{esc(target_url)}">{action}</a></p></article>'
        )
    collection_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{BOOKS_BASE}/tr/#collection",
        "url": f"{BOOKS_BASE}/tr/",
        "name": "Faramarz Kowsari Kitapları — Türkçe katalog",
        "description": "Faramarz Kowsari kitaplarının Türkçe keşif kataloğu; her kitabın gerçek yayın dili, temel konusu ve resmi Google Books bağlantısı açıkça belirtilir.",
        "inLanguage": "tr",
        "isPartOf": {"@id": f"{BOOKS_BASE}/#collection"},
    }
    return f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<title>Faramarz Kowsari Kitapları — Türkçe katalog</title>
<meta name="description" content="Faramarz Kowsari kitaplarının Türkçe kataloğu: kısa tanıtımlar, temel konular, gerçek yayın dili, önizlemeler ve resmi Google Books bağlantıları.">
<link rel="canonical" href="{BOOKS_BASE}/tr/"><link rel="alternate" hreflang="tr" href="{BOOKS_BASE}/tr/"><link rel="alternate" hreflang="ru" href="{BOOKS_BASE}/ru/"><link rel="alternate" hreflang="x-default" href="{BOOKS_BASE}/">
<style>{STYLE}</style><script type="application/ld+json">{json.dumps(collection_schema, ensure_ascii=False)}</script></head>
<body><main><nav class="crumbs"><a href="{BOOKS_BASE}/">← Tüm kitaplar / All books</a></nav><h1>Faramarz Kowsari Kitapları — Türkçe katalog</h1>
<p>Bu sayfa, kitaplığın tamamını Türkçe konuşan okuyucular için düzenler. Türkçe olmayan kitaplar için ayrı Türkçe tanıtım sayfaları kullanılır; kitabın gerçek yayın dili her zaman açıkça belirtilir.</p>
<div class="notice"><strong>Not:</strong> Bu katalogdaki bazı kitaplar Türkçe, bazıları ise başka dillerde yayımlanmıştır. Google Books'a geçmeden önce her kartta ve tanıtım sayfasında yayın dili gösterilir.</div>
<section class="catalog-grid">{''.join(cards)}</section></main></body></html>'''


def write_sitemap(urls):
    body = "\n".join(f"  <url><loc>{xml_escape(url)}</loc></url>" for url in urls)
    (BOOKS / "sitemap-tr.xml").write_text(
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

    catalog_items = []
    generated = 0
    patched_original = 0
    patched_russian = 0
    sitemap_urls = [f"{BOOKS_BASE}/tr/"]

    for book in books:
        slug = str(book.get("slug") or "").strip("/")
        if not slug or book.get("status") != "active":
            continue
        original_path = BOOKS / slug / "index.html"
        if not original_path.exists():
            continue

        meta = turkish_meta(book, overrides.get(slug, {}) if isinstance(overrides.get(slug, {}), dict) else {})
        original_url = f"{BOOKS_BASE}/{slug}/"

        if meta["source_lang"] == "tr":
            catalog_items.append((book, meta, original_url))
            sitemap_urls.append(original_url)
            continue

        tr_url = f"{original_url}tr/"
        outdir = BOOKS / slug / "tr"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "index.html").write_text(render_book(book, meta), encoding="utf-8")
        generated += 1

        if upsert_turkish_alternate(original_path, tr_url):
            patched_original += 1
        russian_path = BOOKS / slug / "ru" / "index.html"
        if russian_path.exists() and upsert_turkish_alternate(russian_path, tr_url):
            patched_russian += 1

        catalog_items.append((book, meta, tr_url))
        sitemap_urls.append(tr_url)

    catalog_items.sort(key=lambda item: (item[0].get("sequence") or 999999, item[0].get("title") or ""))
    catalog_dir = BOOKS / "tr"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "index.html").write_text(render_catalog(catalog_items), encoding="utf-8")
    write_sitemap(sitemap_urls)
    print(
        f"Turkish discovery pages: {generated} generated; "
        f"{len(catalog_items)} books in Turkish catalog; "
        f"{patched_original} original pages and {patched_russian} Russian pages updated with Turkish hreflang; "
        f"sitemap URLs: {len(sitemap_urls)}"
    )


if __name__ == "__main__":
    main()
