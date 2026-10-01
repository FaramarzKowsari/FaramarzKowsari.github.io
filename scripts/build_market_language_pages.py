#!/usr/bin/env python3
"""Build German, Spanish, French and Brazilian-Portuguese discovery pages.

This generator extends the book library's existing Russian/Turkish localization
architecture without changing a book's actual publication language.

For each configured market language it:
- creates /books/<slug>/<locale>/ when the book is published in another language;
- uses the original /books/<slug>/ URL when the book itself is already in that language;
- creates a localized catalog at /books/<locale>/;
- creates /books/sitemap-<locale>.xml;
- injects one reciprocal hreflang cluster across original, RU/TR and market pages;
- keeps Book structured-data inLanguage equal to the real publication language;
- supports optional hand-edited overrides in books/localizations/<locale>.json.

Localized copy is deliberately grounded in public books.json metadata. Original
synopsis/audience/learning text is shown as source-language material instead of
being silently machine-translated or embellished.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
from xml.sax.saxutils import escape as xml_escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
SITE = "https://faramarzkowsari.github.io"
BOOKS_BASE = f"{SITE}/books"
AUTHOR = "Faramarz Kowsari"

LANG_CODES = {
    "English": "en", "Türkçe": "tr", "Turkish": "tr",
    "Español": "es", "Spanish": "es", "Español (España)": "es",
    "Français": "fr", "French": "fr", "Deutsch": "de", "German": "de",
    "فارسی": "fa", "Persian": "fa", "Português": "pt", "Portuguese": "pt",
    "Português (Brasil)": "pt-BR", "Brazilian Portuguese": "pt-BR",
    "Romanian": "ro", "Română": "ro", "Indonesian": "id",
    "Bahasa Indonesia": "id", "Filipino": "fil", "Русский": "ru",
    "Russian": "ru", "Arabic": "ar", "العربية": "ar",
}

SOURCE_LANGUAGE_NAMES = {
    "de": {"en": "Englisch", "tr": "Türkisch", "es": "Spanisch", "fr": "Französisch", "de": "Deutsch", "fa": "Persisch", "pt": "Portugiesisch", "pt-BR": "brasilianischem Portugiesisch", "ro": "Rumänisch", "id": "Indonesisch", "fil": "Filipino", "ru": "Russisch", "ar": "Arabisch"},
    "es": {"en": "inglés", "tr": "turco", "es": "español", "fr": "francés", "de": "alemán", "fa": "persa", "pt": "portugués", "pt-BR": "portugués de Brasil", "ro": "rumano", "id": "indonesio", "fil": "filipino", "ru": "ruso", "ar": "árabe"},
    "fr": {"en": "anglais", "tr": "turc", "es": "espagnol", "fr": "français", "de": "allemand", "fa": "persan", "pt": "portugais", "pt-BR": "portugais du Brésil", "ro": "roumain", "id": "indonésien", "fil": "filipino", "ru": "russe", "ar": "arabe"},
    "pt-BR": {"en": "inglês", "tr": "turco", "es": "espanhol", "fr": "francês", "de": "alemão", "fa": "persa", "pt": "português", "pt-BR": "português do Brasil", "ro": "romeno", "id": "indonésio", "fil": "filipino", "ru": "russo", "ar": "árabe"},
}

CATEGORY_KEYS = [
    ("ai", ("artificial intelligence", " ai ", "prompt", "chatgpt", "claude", "agent", "llm", "generative ai")),
    ("data", ("machine learning", "data science", "sql", "python", "analytics", "data analysis", "decision tree")),
    ("trading", ("trading", "forex", "crypto", "options", "order block", "liquidity", "wyckoff", "macd", "smc", "market structure", "financial market")),
    ("finance", ("finance", "money", "financial", "econom", "installment", "poverty", "debt")),
    ("business", ("business", "e-commerce", "marketing", "sales", "entrepreneur", "small business", "social media")),
    ("psychology", ("psychology", "mindfulness", "personal development", "relationship", "mind", "love", "infidelity")),
    ("language", ("language", "turkish", "grammar", "english", "vocabulary")),
    ("resilience", ("weather", "heat", "air quality", "earthquake", "disaster", "survival", "resilience")),
]

LOCALIZED_CATEGORIES = {
    "de": {
        "ai": ("Künstliche Intelligenz", "Der öffentliche Buchdatensatz ordnet diesen Titel Themen rund um künstliche Intelligenz, moderne AI-Werkzeuge oder Prompt-basierte Arbeitsabläufe zu."),
        "data": ("Data Science und Machine Learning", "Die veröffentlichten Metadaten verorten den Titel in Data Science, Datenanalyse oder Machine Learning und nennen dazugehörige praktische Schwerpunkte."),
        "trading": ("Trading und Finanzmärkte", "Die Buchmetadaten nennen Trading, Marktstruktur, Liquidität, Risiko oder verwandte Konzepte als zentrale Orientierungspunkte."),
        "finance": ("Persönliche Finanzen und Wirtschaft", "Der Titel behandelt laut öffentlicher Beschreibung finanzielle Entscheidungen, Geld, wirtschaftliche Rahmenbedingungen oder verwandte Themen."),
        "business": ("Business, Marketing und Unternehmertum", "Die Metadaten weisen auf praxisnahe Themen aus Strategie, Marketing, Verkauf, E-Commerce oder Unternehmensführung hin."),
        "psychology": ("Psychologie und persönliche Entwicklung", "Der öffentliche Datensatz nennt Themen wie Verhalten, Beziehungen, Achtsamkeit oder persönliche Entwicklung."),
        "language": ("Sprachenlernen", "Der Titel gehört laut Metadaten zum Sprachenlernen und arbeitet mit Grammatik, Wortschatz, Beispielen oder strukturiertem Üben."),
        "resilience": ("Sicherheit, Klima und Resilienz", "Die Buchbeschreibung verknüpft den Titel mit Risiko, Vorbereitung, Sicherheit, Klima, Katastrophen oder Resilienz."),
        "default": ("Praxisorientiertes Lernen", "Die öffentliche Buchbeschreibung präsentiert den Titel als strukturierten, anwendungsorientierten Leitfaden mit klar benannten Themen und Lernzielen."),
    },
    "es": {
        "ai": ("inteligencia artificial", "Los metadatos públicos sitúan este título en temas de inteligencia artificial, herramientas modernas de IA o flujos de trabajo basados en prompts."),
        "data": ("ciencia de datos y aprendizaje automático", "Los metadatos publicados relacionan el libro con ciencia de datos, análisis, SQL, Python o aprendizaje automático y señalan objetivos prácticos."),
        "trading": ("trading y mercados financieros", "La ficha pública destaca trading, estructura de mercado, liquidez, riesgo u otros conceptos relacionados como ejes del libro."),
        "finance": ("finanzas personales y economía", "La descripción pública vincula el título con decisiones financieras, dinero, economía, deuda u otros temas afines."),
        "business": ("negocios, marketing y emprendimiento", "Los metadatos señalan temas prácticos de estrategia, marketing, ventas, comercio electrónico o gestión empresarial."),
        "psychology": ("psicología y desarrollo personal", "La ficha pública menciona comportamiento, relaciones, atención plena o desarrollo personal entre sus áreas temáticas."),
        "language": ("aprendizaje de idiomas", "Según los metadatos, el título está orientado al aprendizaje de idiomas mediante gramática, vocabulario, ejemplos o práctica estructurada."),
        "resilience": ("seguridad, clima y resiliencia", "La descripción pública relaciona el libro con riesgos, preparación, seguridad, clima, desastres o resiliencia."),
        "default": ("aprendizaje práctico", "La descripción pública presenta el título como un recurso estructurado y práctico con temas y objetivos de aprendizaje claramente identificados."),
    },
    "fr": {
        "ai": ("intelligence artificielle", "Les métadonnées publiques rattachent ce titre à l'intelligence artificielle, aux outils d'IA modernes ou aux flux de travail fondés sur les prompts."),
        "data": ("data science et apprentissage automatique", "Les métadonnées publiées relient le livre à la data science, à l'analyse, à SQL, Python ou au machine learning, avec des objectifs pratiques."),
        "trading": ("trading et marchés financiers", "La fiche publique met en avant le trading, la structure de marché, la liquidité, le risque ou des concepts connexes."),
        "finance": ("finances personnelles et économie", "La description publique associe le titre aux décisions financières, à l'argent, à l'économie, à la dette ou à des thèmes proches."),
        "business": ("entreprise, marketing et entrepreneuriat", "Les métadonnées signalent des thèmes pratiques de stratégie, marketing, vente, e-commerce ou gestion d'entreprise."),
        "psychology": ("psychologie et développement personnel", "La fiche publique mentionne le comportement, les relations, la pleine conscience ou le développement personnel parmi ses axes."),
        "language": ("apprentissage des langues", "Selon les métadonnées, le titre soutient l'apprentissage des langues par la grammaire, le vocabulaire, des exemples ou une pratique structurée."),
        "resilience": ("sécurité, climat et résilience", "La description publique relie le livre aux risques, à la préparation, à la sécurité, au climat, aux catastrophes ou à la résilience."),
        "default": ("apprentissage pratique", "La description publique présente le titre comme une ressource structurée et orientée vers la pratique, avec des thèmes et objectifs clairement identifiés."),
    },
    "pt-BR": {
        "ai": ("inteligência artificial", "Os metadados públicos situam este título em inteligência artificial, ferramentas modernas de IA ou fluxos de trabalho baseados em prompts."),
        "data": ("ciência de dados e aprendizado de máquina", "Os metadados publicados relacionam o livro a ciência de dados, análise, SQL, Python ou machine learning e indicam objetivos práticos."),
        "trading": ("trading e mercados financeiros", "A ficha pública destaca trading, estrutura de mercado, liquidez, risco ou conceitos relacionados como eixos do livro."),
        "finance": ("finanças pessoais e economia", "A descrição pública associa o título a decisões financeiras, dinheiro, economia, dívida ou outros temas próximos."),
        "business": ("negócios, marketing e empreendedorismo", "Os metadados apontam temas práticos de estratégia, marketing, vendas, comércio eletrônico ou gestão empresarial."),
        "psychology": ("psicologia e desenvolvimento pessoal", "A ficha pública menciona comportamento, relacionamentos, atenção plena ou desenvolvimento pessoal entre as áreas do título."),
        "language": ("aprendizado de idiomas", "Segundo os metadados, o título apoia o aprendizado de idiomas com gramática, vocabulário, exemplos ou prática estruturada."),
        "resilience": ("segurança, clima e resiliência", "A descrição pública relaciona o livro a riscos, preparação, segurança, clima, desastres ou resiliência."),
        "default": ("aprendizado prático", "A descrição pública apresenta o título como um recurso estruturado e prático, com temas e objetivos de aprendizagem claramente identificados."),
    },
}

LOCALES = {
    "de": {
        "hreflang": "de", "html_lang": "de", "og_locale": "de_DE", "name": "Deutsch",
        "catalog_title": "Bücher von Faramarz Kowsari auf Deutsch entdecken",
        "catalog_intro": "Deutschsprachiger Entdeckungskatalog der öffentlichen Buchbibliothek. Jede Seite nennt die tatsächliche Publikationssprache und führt zur offiziellen Google-Books-Seite, sofern vorhanden.",
        "page_label": "Deutschsprachige Buchvorstellung", "books": "Bücher", "catalog": "Deutscher Katalog",
        "about": "Worum geht es in diesem Buch?", "topics": "Ausgewiesene Schwerpunkte", "source": "Originale öffentliche Buchbeschreibung",
        "audience": "Für wen ist das Buch gedacht?", "learning": "Ausgewiesene Lernziele", "language": "Publikationssprache",
        "notice": "Diese Seite ist eine deutschsprachige Orientierung. Das eigentliche Buch ist in {language} veröffentlicht; Titel, Vorschau und Kaufoptionen auf Google Books beziehen sich auf diese Ausgabe.",
        "google": "Auf Google Books ansehen", "preview": "Kostenlose Vorschau öffnen", "original": "Originale Buchseite", "back": "Zurück zum deutschen Katalog",
        "seo": "{title}: deutschsprachige Buchvorstellung mit Themen, Zielgruppe, Publikationssprache, Google-Books-Link und Vorschau. Das Buch ist in {language} veröffentlicht.",
        "summary": "„{title}“ ist ein Buch von Faramarz Kowsari im Bereich {category}. Diese deutschsprachige Entdeckungsseite ordnet den Titel anhand der veröffentlichten Buchmetadaten ein und macht Themen, Zielgruppe, Publikationssprache sowie offizielle Lese- und Kaufwege leichter auffindbar.",
        "audience_text": "Die Zielgruppe ergibt sich aus der öffentlichen Buchbeschreibung. Für deutschsprachige Leser ist besonders wichtig, dass die eigentliche Ausgabe in {language} vorliegt.",
    },
    "es": {
        "hreflang": "es", "html_lang": "es", "og_locale": "es_ES", "name": "Español",
        "catalog_title": "Descubre los libros de Faramarz Kowsari en español",
        "catalog_intro": "Catálogo de descubrimiento en español de la biblioteca pública. Cada página indica el idioma real de publicación y enlaza con la edición oficial en Google Books cuando está disponible.",
        "page_label": "Presentación del libro en español", "books": "Libros", "catalog": "Catálogo en español",
        "about": "¿De qué trata este libro?", "topics": "Temas destacados", "source": "Descripción pública original del libro",
        "audience": "¿A quién va dirigido?", "learning": "Objetivos de aprendizaje publicados", "language": "Idioma de publicación",
        "notice": "Esta es una página de orientación en español. El libro se publica en {language}; el título, la vista previa y las opciones de compra de Google Books corresponden a esa edición.",
        "google": "Ver en Google Books", "preview": "Abrir vista previa gratuita", "original": "Página original del libro", "back": "Volver al catálogo en español",
        "seo": "{title}: presentación en español con temas, público, idioma de publicación, enlace oficial a Google Books y vista previa. El libro está publicado en {language}.",
        "summary": "“{title}” es un libro de Faramarz Kowsari dentro del área de {category}. Esta página de descubrimiento en español organiza la información pública del libro para que sus temas, público, idioma real de publicación y vías oficiales de lectura o compra sean más fáciles de encontrar.",
        "audience_text": "El público objetivo se basa en la descripción pública del libro. Para lectores hispanohablantes, conviene tener presente que la edición disponible está publicada en {language}.",
    },
    "fr": {
        "hreflang": "fr", "html_lang": "fr", "og_locale": "fr_FR", "name": "Français",
        "catalog_title": "Découvrir les livres de Faramarz Kowsari en français",
        "catalog_intro": "Catalogue de découverte en français de la bibliothèque publique. Chaque page indique la langue réelle de publication et renvoie vers l'édition officielle sur Google Books lorsqu'elle est disponible.",
        "page_label": "Présentation du livre en français", "books": "Livres", "catalog": "Catalogue français",
        "about": "De quoi parle ce livre ?", "topics": "Thèmes mis en avant", "source": "Description publique originale du livre",
        "audience": "À qui s'adresse le livre ?", "learning": "Objectifs d'apprentissage publiés", "language": "Langue de publication",
        "notice": "Cette page est une orientation en français. Le livre lui-même est publié en {language} ; le titre, l'aperçu et les options d'achat sur Google Books correspondent à cette édition.",
        "google": "Voir sur Google Books", "preview": "Ouvrir l'aperçu gratuit", "original": "Page originale du livre", "back": "Retour au catalogue français",
        "seo": "{title} : présentation en français avec thèmes, public, langue de publication, lien Google Books et aperçu. Le livre est publié en {language}.",
        "summary": "« {title} » est un livre de Faramarz Kowsari dans le domaine {category}. Cette page de découverte en français organise les métadonnées publiques du livre afin de rendre ses thèmes, son public, sa langue réelle de publication et ses accès officiels plus faciles à trouver.",
        "audience_text": "Le public visé est fondé sur la description publique du livre. Pour les lecteurs francophones, il faut noter que l'édition disponible est publiée en {language}.",
    },
    "pt-br": {
        "hreflang": "pt-BR", "html_lang": "pt-BR", "og_locale": "pt_BR", "name": "Português do Brasil",
        "catalog_title": "Descubra os livros de Faramarz Kowsari em português do Brasil",
        "catalog_intro": "Catálogo de descoberta em português do Brasil da biblioteca pública. Cada página informa o idioma real de publicação e aponta para a edição oficial no Google Books quando disponível.",
        "page_label": "Apresentação do livro em português do Brasil", "books": "Livros", "catalog": "Catálogo em português do Brasil",
        "about": "Sobre o que é este livro?", "topics": "Temas em destaque", "source": "Descrição pública original do livro",
        "audience": "Para quem é este livro?", "learning": "Objetivos de aprendizagem publicados", "language": "Idioma de publicação",
        "notice": "Esta é uma página de orientação em português do Brasil. O livro é publicado em {language}; título, prévia e opções de compra no Google Books correspondem a essa edição.",
        "google": "Ver no Google Books", "preview": "Abrir prévia gratuita", "original": "Página original do livro", "back": "Voltar ao catálogo em português do Brasil",
        "seo": "{title}: apresentação em português do Brasil com temas, público, idioma de publicação, link oficial do Google Books e prévia. O livro é publicado em {language}.",
        "summary": "“{title}” é um livro de Faramarz Kowsari na área de {category}. Esta página de descoberta em português do Brasil organiza os metadados públicos para tornar mais fáceis de encontrar os temas, o público, o idioma real de publicação e os caminhos oficiais de leitura ou compra.",
        "audience_text": "O público-alvo é baseado na descrição pública do livro. Para leitores brasileiros, é importante observar que a edição disponível está publicada em {language}.",
    },
}

ALL_LOCALE_PATHS = {
    "ru": "ru",
    "tr": "tr",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "pt-BR": "pt-br",
}

STYLE = """
:root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.68;background:#f5f7fb;color:#172033}a{color:#1259c3}main{max-width:1060px;margin:auto;padding:28px 20px 64px}.crumbs{font-size:.95rem;margin-bottom:20px}.hero{display:grid;grid-template-columns:minmax(170px,255px) 1fr;gap:30px;align-items:start;background:#fff;border:1px solid #dfe5ef;border-radius:20px;padding:24px;box-shadow:0 12px 34px rgba(24,40,72,.08)}.hero img{width:100%;border-radius:12px;box-shadow:0 8px 22px rgba(0,0,0,.16)}h1{line-height:1.18;margin:.08em 0 .35em;font-size:clamp(1.9rem,5vw,3.2rem)}h2{margin-top:0}.subtitle{font-size:1.05rem;color:#4d5b70}.badge{display:inline-block;background:#eef4ff;color:#154b94;border-radius:999px;padding:6px 11px;margin:3px 5px 3px 0;font-size:.9rem}.notice{background:#fff6dc;border:1px solid #edd28a;border-radius:12px;padding:12px 14px;margin:16px 0}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.btn{display:inline-block;padding:11px 15px;border-radius:10px;text-decoration:none;font-weight:700;border:1px solid #cbd5e3;background:#fff}.btn.primary{background:#1557b0;color:#fff;border-color:#1557b0}.section{background:#fff;border:1px solid #dfe5ef;border-radius:16px;padding:22px;margin-top:20px}.topics{display:flex;flex-wrap:wrap;gap:8px}.topic{padding:7px 10px;background:#f2f5f9;border-radius:9px}.source-text{white-space:pre-line;padding:14px 16px;border-left:4px solid #cbd5e3;background:#f8fafc;border-radius:8px}.small{font-size:.92rem;color:#607086}.catalog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:18px}.card{background:#fff;border:1px solid #dfe5ef;border-radius:15px;padding:15px}.card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:9px}.card h2{font-size:1.08rem;margin:.7rem 0 .35rem}.card a{text-decoration:none}.card .small{margin:.3rem 0}.source-list{padding-left:1.2rem}@media(max-width:720px){.hero{grid-template-columns:1fr}.hero img{max-width:240px;margin:auto}}@media(prefers-color-scheme:dark){body{background:#111827;color:#e5e7eb}.hero,.section,.card,.btn{background:#182233;border-color:#334155}.subtitle,.small{color:#b7c2d1}.badge,.topic{background:#26364d;color:#dbeafe}.notice{background:#3d3114;border-color:#756129}.source-text{background:#111827;border-color:#475569}}
""".strip()


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def source_lang(book):
    code = str(book.get("language_code") or "").strip()
    if code:
        return code.replace("_", "-")
    return LANG_CODES.get(book.get("language"), "en")


def language_matches(source: str, target: str) -> bool:
    s = source.lower().replace("_", "-")
    t = target.lower().replace("_", "-")
    if t == "pt-br":
        return s == "pt-br"
    return s == t or s.split("-", 1)[0] == t.split("-", 1)[0]


def language_name(locale_hreflang: str, source: str) -> str:
    names = SOURCE_LANGUAGE_NAMES.get(locale_hreflang, {})
    return names.get(source, names.get(source.split("-", 1)[0], source))


def category_key(book):
    hay = " " + " ".join([
        str(book.get("category") or ""), str(book.get("title") or ""),
        str(book.get("subtitle") or ""),
        " ".join(str(x) for x in (book.get("key_topics") or [])[:12]),
    ]).lower() + " "
    for key, needles in CATEGORY_KEYS:
        if any(needle in hay for needle in needles):
            return key
    return "default"


def active_books():
    data = load_json(DATA, [])
    return [b for b in data if isinstance(b, dict) and b.get("slug") and b.get("status", "active") == "active"]


def overrides_for(path_code):
    data = load_json(BOOKS / "localizations" / f"{path_code}.json", {})
    return data if isinstance(data, dict) else {}


def localized_url(book, hreflang, path_code):
    original = f"{BOOKS_BASE}/{book['slug']}/"
    if language_matches(source_lang(book), hreflang):
        return original
    return f"{original}{path_code}/"


def available_alternates(book):
    original = f"{BOOKS_BASE}/{book['slug']}/"
    src = source_lang(book)
    pairs = [(src, original)]
    for hreflang, path_code in ALL_LOCALE_PATHS.items():
        if language_matches(src, hreflang):
            url = original
        else:
            p = BOOKS / book["slug"] / path_code / "index.html"
            if not p.exists():
                continue
            url = f"{original}{path_code}/"
        pairs.append((hreflang, url))
    dedup = []
    seen = set()
    for lang, url in pairs:
        key = (lang.lower(), url)
        if key not in seen:
            seen.add(key)
            dedup.append((lang, url))
    return dedup


def hreflang_block(book):
    links = [f'<link rel="alternate" hreflang="{esc(lang)}" href="{esc(url)}">' for lang, url in available_alternates(book)]
    original = f"{BOOKS_BASE}/{book['slug']}/"
    links.append(f'<link rel="alternate" hreflang="x-default" href="{esc(original)}">')
    return "<!-- multilingual-localizations:start -->\n" + "\n".join(links) + "\n<!-- multilingual-localizations:end -->"


OLD_BLOCKS = [
    re.compile(r"\n?<!-- russian-localization:start -->.*?<!-- russian-localization:end -->", re.S),
    re.compile(r"\n?<!-- turkish-localization:start -->.*?<!-- turkish-localization:end -->", re.S),
    re.compile(r"\n?<!-- multilingual-localizations:start -->.*?<!-- multilingual-localizations:end -->", re.S),
]


def upsert_book_alternates(path: pathlib.Path, book):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    new = text
    for pattern in OLD_BLOCKS:
        new = pattern.sub("", new)
    block = hreflang_block(book)
    if "</head>" not in new:
        return False
    new = new.replace("</head>", block + "\n</head>", 1)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def truncate(text, limit=1400):
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return cut + "…"


def localized_meta(book, path_code, override):
    cfg = LOCALES[path_code]
    lang = cfg["hreflang"]
    src = source_lang(book)
    src_name = language_name(lang, src)
    cat_key = category_key(book)
    category, profile = LOCALIZED_CATEGORIES[lang][cat_key]
    title = str(book.get("title") or "Untitled")
    meta = {
        "title": override.get("title") or title,
        "category": override.get("category") or category,
        "profile": override.get("profile") or profile,
        "source_lang": src,
        "source_lang_name": src_name,
    }
    meta["summary"] = override.get("summary") or cfg["summary"].format(title=title, category=meta["category"])
    meta["seo"] = override.get("seo_description") or cfg["seo"].format(title=title, language=src_name)
    meta["audience_text"] = override.get("audience") or cfg["audience_text"].format(language=src_name)
    return meta


def schema_for(book, path_code, meta, canonical):
    original = f"{BOOKS_BASE}/{book['slug']}/"
    google = book.get("google_books_url") or ""
    cover = book.get("cover_url") or ""
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": f"{book.get('title') or 'Untitled'} — {LOCALES[path_code]['page_label']}",
        "description": meta["seo"],
        "inLanguage": LOCALES[path_code]["hreflang"],
        "isPartOf": {"@type": "CollectionPage", "url": f"{BOOKS_BASE}/{path_code}/"},
        "mainEntity": {
            "@type": "Book",
            "@id": original + "#book",
            "name": book.get("title") or "Untitled",
            "author": {"@type": "Person", "@id": f"{SITE}/#person", "name": AUTHOR},
            "inLanguage": meta["source_lang"],
            "url": original,
            "sameAs": google or original,
            "image": cover,
        },
    }


def render_book(book, path_code, override):
    cfg = LOCALES[path_code]
    meta = localized_meta(book, path_code, override)
    slug = book["slug"]
    original = f"{BOOKS_BASE}/{slug}/"
    canonical = f"{original}{path_code}/"
    title = str(book.get("title") or "Untitled")
    subtitle = str(book.get("subtitle") or "").strip()
    cover = str(book.get("cover_url") or "").strip()
    google = str(book.get("google_books_url") or "").strip()
    gid = str(book.get("google_books_id") or "").strip()
    preview = f"https://play.google.com/books/reader?id={gid}&hl={cfg['hreflang']}" if gid else ""
    topics = [str(x).strip() for x in (book.get("key_topics") or []) if str(x).strip()][:14]
    source_summary = truncate(book.get("summary") or book.get("description") or "", 1800)
    source_audience = truncate(book.get("target_audience") or "", 700)
    source_learning = [str(x).strip() for x in (book.get("learning") or []) if str(x).strip()][:8]
    keywords = ", ".join([title, meta["category"], AUTHOR] + topics[:10])
    schema = schema_for(book, path_code, meta, canonical)

    topic_html = "".join(f'<span class="topic">{esc(t)}</span>' for t in topics) or '<span class="small">—</span>'
    learning_html = "".join(f"<li>{esc(x)}</li>" for x in source_learning)
    source_sections = ""
    if source_summary:
        source_sections += f'<section class="section"><h2>{esc(cfg["source"])}</h2><p class="small">{esc(meta["source_lang_name"])}</p><div class="source-text">{esc(source_summary)}</div></section>'
    if source_audience:
        source_sections += f'<section class="section"><h2>{esc(cfg["audience"])}</h2><p>{esc(meta["audience_text"])}</p><div class="source-text">{esc(source_audience)}</div></section>'
    else:
        source_sections += f'<section class="section"><h2>{esc(cfg["audience"])}</h2><p>{esc(meta["audience_text"])}</p></section>'
    if learning_html:
        source_sections += f'<section class="section"><h2>{esc(cfg["learning"])}</h2><p class="small">{esc(meta["source_lang_name"])}</p><ul class="source-list">{learning_html}</ul></section>'

    actions = []
    if google:
        actions.append(f'<a class="btn primary" href="{esc(google)}" rel="noopener">{esc(cfg["google"])}</a>')
    if preview:
        actions.append(f'<a class="btn" href="{esc(preview)}" rel="noopener">{esc(cfg["preview"])}</a>')
    actions.append(f'<a class="btn" href="{esc(original)}">{esc(cfg["original"])}</a>')

    cover_html = f'<img src="{esc(cover)}" alt="{esc(title)}" loading="eager" decoding="async">' if cover else ""
    subtitle_html = f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ""

    return f'''<!doctype html>
<html lang="{esc(cfg['html_lang'])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — {esc(cfg['page_label'])} | Faramarz Kowsari</title>
<meta name="description" content="{esc(meta['seo'])}">
<meta name="keywords" content="{esc(keywords)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)} — {esc(cfg['page_label'])}">
<meta property="og:description" content="{esc(meta['seo'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:locale" content="{esc(cfg['og_locale'])}">
{f'<meta property="og:image" content="{esc(cover)}">' if cover else ''}
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>
</head>
<body>
<main>
<nav class="crumbs"><a href="{BOOKS_BASE}/">{esc(cfg['books'])}</a> › <a href="{BOOKS_BASE}/{path_code}/">{esc(cfg['catalog'])}</a> › {esc(title)}</nav>
<section class="hero">
<div>{cover_html}</div>
<div>
<span class="badge">{esc(cfg['page_label'])}</span><span class="badge">{esc(meta['category'])}</span>
<h1>{esc(title)}</h1>{subtitle_html}
<p>{esc(meta['summary'])}</p>
<p>{esc(meta['profile'])}</p>
<div class="notice"><strong>{esc(cfg['language'])}:</strong> {esc(meta['source_lang_name'])}. {esc(cfg['notice'].format(language=meta['source_lang_name']))}</div>
<div class="actions">{''.join(actions)}</div>
</div>
</section>
<section class="section"><h2>{esc(cfg['about'])}</h2><p>{esc(meta['summary'])}</p><p>{esc(meta['profile'])}</p></section>
<section class="section"><h2>{esc(cfg['topics'])}</h2><div class="topics">{topic_html}</div></section>
{source_sections}
<p class="small"><a href="{BOOKS_BASE}/{path_code}/">← {esc(cfg['back'])}</a></p>
</main>
</body>
</html>
'''


def render_catalog(books, path_code):
    cfg = LOCALES[path_code]
    cards = []
    for book in sorted(books, key=lambda x: (int(x.get("sequence") or 999999), str(x.get("title") or ""))):
        title = str(book.get("title") or "Untitled")
        cover = str(book.get("cover_url") or "").strip()
        src = source_lang(book)
        src_name = language_name(cfg["hreflang"], src)
        if language_matches(src, cfg["hreflang"]):
            url = f"{BOOKS_BASE}/{book['slug']}/"
        else:
            url = f"{BOOKS_BASE}/{book['slug']}/{path_code}/"
        img = f'<img src="{esc(cover)}" alt="{esc(title)}" loading="lazy" decoding="async">' if cover else ""
        cards.append(f'<article class="card"><a href="{esc(url)}">{img}<h2>{esc(title)}</h2></a><p class="small">{esc(cfg["language"])}: {esc(src_name)}</p></article>')

    canonical = f"{BOOKS_BASE}/{path_code}/"
    schema = {
        "@context": "https://schema.org", "@type": "CollectionPage", "url": canonical,
        "name": cfg["catalog_title"], "description": cfg["catalog_intro"],
        "inLanguage": cfg["hreflang"], "isPartOf": {"@type": "WebSite", "url": SITE + "/"},
    }
    return f'''<!doctype html>
<html lang="{esc(cfg['html_lang'])}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(cfg['catalog_title'])} | Faramarz Kowsari</title>
<meta name="description" content="{esc(cfg['catalog_intro'])}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(cfg['catalog_title'])}"><meta property="og:description" content="{esc(cfg['catalog_intro'])}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:locale" content="{esc(cfg['og_locale'])}">
<style>{STYLE}</style>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>
</head>
<body><main><nav class="crumbs"><a href="{BOOKS_BASE}/">{esc(cfg['books'])}</a></nav><section class="section"><h1>{esc(cfg['catalog_title'])}</h1><p>{esc(cfg['catalog_intro'])}</p><p class="small">{len(books)} titles</p></section><section class="catalog-grid">{''.join(cards)}</section></main></body>
</html>
'''


def catalog_hreflang_block():
    links = [f'<link rel="alternate" hreflang="en" href="{BOOKS_BASE}/">']
    for hreflang, path_code in ALL_LOCALE_PATHS.items():
        p = BOOKS / path_code / "index.html"
        if p.exists():
            links.append(f'<link rel="alternate" hreflang="{esc(hreflang)}" href="{BOOKS_BASE}/{path_code}/">')
    links.append(f'<link rel="alternate" hreflang="x-default" href="{BOOKS_BASE}/">')
    return "<!-- multilingual-localizations:start -->\n" + "\n".join(links) + "\n<!-- multilingual-localizations:end -->"


def upsert_catalog_alternates(path):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    new = text
    for pattern in OLD_BLOCKS:
        new = pattern.sub("", new)
    if "</head>" not in new:
        return False
    new = new.replace("</head>", catalog_hreflang_block() + "\n</head>", 1)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def write_sitemap(path_code, books):
    cfg = LOCALES[path_code]
    urls = [f"{BOOKS_BASE}/{path_code}/"]
    for book in books:
        urls.append(localized_url(book, cfg["hreflang"], path_code))
    seen = set()
    urls = [u for u in urls if not (u in seen or seen.add(u))]
    body = "\n".join(f"  <url><loc>{xml_escape(u)}</loc></url>" for u in urls)
    (BOOKS / f"sitemap-{path_code}.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body + '\n</urlset>\n', encoding="utf-8"
    )
    return len(urls)


def main():
    books = active_books()
    if not books:
        raise SystemExit("No active books found in books/books.json")

    generated = {code: 0 for code in LOCALES}
    sitemap_counts = {}

    for path_code, cfg in LOCALES.items():
        overrides = overrides_for(path_code)
        for book in books:
            if language_matches(source_lang(book), cfg["hreflang"]):
                continue
            out = BOOKS / book["slug"] / path_code / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            override = overrides.get(book["slug"], {}) if isinstance(overrides.get(book["slug"], {}), dict) else {}
            out.write_text(render_book(book, path_code, override), encoding="utf-8")
            generated[path_code] += 1
        catalog_dir = BOOKS / path_code
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "index.html").write_text(render_catalog(books, path_code), encoding="utf-8")
        sitemap_counts[path_code] = write_sitemap(path_code, books)

    touched = 0
    for book in books:
        candidates = [BOOKS / book["slug"] / "index.html"]
        for path_code in set(ALL_LOCALE_PATHS.values()):
            candidates.append(BOOKS / book["slug"] / path_code / "index.html")
        for path in candidates:
            if path.exists() and upsert_book_alternates(path, book):
                touched += 1

    for path in [BOOKS / "index.html"] + [BOOKS / code / "index.html" for code in set(ALL_LOCALE_PATHS.values())]:
        if path.exists():
            upsert_catalog_alternates(path)

    print(
        "Market-language discovery pages: "
        + ", ".join(f"{code}={generated[code]} generated / {sitemap_counts[code]} sitemap URLs" for code in LOCALES)
        + f"; hreflang-updated files={touched}."
    )


if __name__ == "__main__":
    main()
