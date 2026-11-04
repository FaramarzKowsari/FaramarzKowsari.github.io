#!/usr/bin/env python3
"""Apply a consistent editorial presentation to canonical book landing pages.

Only adds semantics, navigation, and a reusable author card. It deliberately
preserves existing book-specific copy, outbound destinations, and cover assets.
This operation is idempotent so it can run at the end of the books build.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html import escape, unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
SKIP = {"all-books", "author", "covers", "topics", "de", "es", "fr", "pt-br", "ru", "tr"}
VERSION = "2026-11"
MAIN_RE = re.compile(r'<main\b[^>]*\bclass="([^"]*\bbook-page\b[^"]*)"[^>]*>', re.I)
HEADING_RE = re.compile(
    r'(<section\b(?P<attrs>[^>]*)>)(?P<gap>\s*)'
    r'(<h2\b[^>]*>)(?P<heading>[^<]+)(</h2>)',
    re.I | re.S,
)
BOOK_TOP_RE = re.compile(r'(<section\b[^>]*class="[^"]*\bbook-top\b[^"]*"[^>]*>.*?</section>)', re.I | re.S)
LINK_RE = re.compile(r'\b(?:href|src)="([^"]+)"', re.I)

SECTION_LABELS = {
    "about": ("About this book", "Kitap hakkında", "Sobre este libro", "À propos de ce livre", "Über dieses Buch", "О книге"),
    "learning": ("What you will learn", "Neler öğreneceksiniz", "Lo que aprenderás", "Ce que vous apprendrez", "Was Sie lernen", "Чему вы научитесь"),
    "topics": ("Key topics", "Temel konular", "Temas clave", "Sujets clés", "Wichtige Themen", "Ключевые темы"),
    "audience": ("Who this book is for", "Bu kitap kimler için?", "Para quién es este libro", "À qui s'adresse ce livre", "Für wen dieses Buch gedacht ist", "Для кого эта книга"),
    "related": ("Related books", "İlgili kitaplar", "Libros relacionados", "Livres associés", "Ähnliche Bücher", "Похожие книги"),
}
NAV_LABELS = {
    "en": ("In this book", ["Overview", "What you'll learn", "Topics", "Readers", "Related"]),
    "tr": ("Bu kitapta", ["Genel bakış", "Öğrenecekleriniz", "Konular", "Okurlar", "İlgili kitaplar"]),
    "es": ("En este libro", ["Resumen", "Aprendizajes", "Temas", "Lectores", "Relacionados"]),
    "de": ("In diesem Buch", ["Überblick", "Lernziele", "Themen", "Leser", "Ähnliche Bücher"]),
    "fr": ("Dans ce livre", ["Présentation", "Objectifs", "Sujets", "Public", "Livres associés"]),
    "ru": ("В этой книге", ["Обзор", "Результаты", "Темы", "Читатели", "Похожие книги"]),
}
AUTHOR_BIOS = {
    "en": (
        "About the author",
        "Faramarz Kowsari is an Istanbul-based author and researcher working at the intersection of technology, education and personal growth. He has published over 160 digital titles on international platforms. His interests include artificial intelligence, prompt engineering, modern trading strategies, classical literature and mindfulness. He also develops web-based educational tools and specialized instructional videos.",
    ),
    "tr": (
        "Yazar hakkında",
        "Faramarz Kowsari, İstanbul'da yaşayan bir yazar ve araştırmacıdır. Teknoloji, eğitim ve kişisel gelişim alanlarında çalışır; uluslararası platformlarda 160'tan fazla dijital eser yayımlamıştır. İlgi alanları yapay zekâ, prompt mühendisliği, modern işlem stratejileri, klasik edebiyat ve farkındalıktır. Ayrıca web tabanlı eğitim araçları ve uzmanlık videoları geliştirir.",
    ),
    "es": (
        "Sobre el autor",
        "Faramarz Kowsari es un autor e investigador residente en Estambul. Trabaja en la intersección de la tecnología, la educación y el desarrollo personal, y ha publicado más de 160 títulos digitales en plataformas internacionales. Sus intereses abarcan la inteligencia artificial, la ingeniería de prompts, las estrategias modernas de trading, la literatura clásica y la atención plena. También desarrolla herramientas educativas en línea y vídeos especializados.",
    ),
    "de": (
        "Über den Autor",
        "Faramarz Kowsari ist ein in Istanbul ansässiger Autor und Forscher. Er beschäftigt sich mit Technologie, Bildung und persönlicher Entwicklung und hat über 160 digitale Titel auf internationalen Plattformen veröffentlicht. Zu seinen Themen zählen künstliche Intelligenz, Prompt Engineering, moderne Handelsstrategien, klassische Literatur und Achtsamkeit. Daneben entwickelt er webbasierte Lernwerkzeuge und Fachvideos.",
    ),
    "fr": (
        "À propos de l’auteur",
        "Faramarz Kowsari est un auteur et chercheur installé à Istanbul. Il travaille à la rencontre de la technologie, de l'éducation et du développement personnel et a publié plus de 160 titres numériques sur des plateformes internationales. Ses domaines d'intérêt comprennent l'intelligence artificielle, le prompt engineering, les stratégies de trading, la littérature classique et la pleine conscience. Il crée également des outils pédagogiques en ligne et des vidéos spécialisées.",
    ),
    "ru": (
        "Об авторе",
        "Faramarz Kowsari — автор и исследователь из Стамбула. Его работы посвящены технологиям, образованию и личностному развитию; на международных платформах опубликовано более 160 его цифровых книг. Среди его тем — искусственный интеллект, промпт-инжиниринг, современные торговые стратегии, классическая литература и осознанность. Он также создаёт учебные веб-инструменты и специализированные видеоматериалы.",
    ),
}


def classification(slug: str, record: dict, page: str) -> str:
    title = record.get("title", "")
    category = record.get("category", "")
    haystack = f"{slug} {title} {category}".lower()
    if any(x in haystack for x in ("trading", "forex", "futures", "options", "scalping", "order-flow", "ichimoku", "smart-money", "xauusd", "wyckoff", "market-structure")):
        return "trading"
    if any(x in haystack for x in ("machine-learning", "data-science", "artificial-intelligence", "cybersecurity", "ai-", "rag-", "claude", "prompt", "llm", "agentic")):
        return "ai"
    if any(x in haystack for x in ("narciss", "psycholog", "relationship", "relaciones", "ilişki", "micro-cheating")):
        return "psychology"
    if any(x in haystack for x in ("turkish", "ielts", "english", "language", "türkçe", "gramm")):
        return "language"
    if any(x in haystack for x in ("business", "finance", "wealth", "money", "income", "e-commerce", "servet", "dinero")):
        return "business"
    return "growth"


def section_kind(heading: str) -> str | None:
    heading = unescape(heading).strip().casefold().rstrip(":")
    for kind, labels in SECTION_LABELS.items():
        if any(heading == label.casefold().rstrip(":") for label in labels):
            return kind
    return None


def author_card(lang: str) -> str:
    heading, bio = AUTHOR_BIOS.get(lang, AUTHOR_BIOS["en"])
    return (
        '\n<section class="section premium-author" id="premium-author" aria-label="Author profile">'
        f'<h2>{escape(heading)}</h2><p>{escape(bio)}</p>'
        '<p class="author-links">'
        '<a href="https://faramarzkowsari.github.io/">Official Website</a>'
        '<a href="https://faramarzkowsari.github.io/books/">Published Books</a>'
        '<a href="https://faramarzkowsari.github.io/books/author/">Author Profile</a>'
        '<a href="https://github.com/FaramarzKowsari" target="_blank" rel="noopener noreferrer">GitHub</a>'
        '<a href="https://orcid.org/0000-0003-1692-0453" target="_blank" rel="noopener noreferrer">ORCID</a>'
        '</p></section>\n'
    )


def premiumize(source: str, slug: str, record: dict) -> tuple[str, dict]:
    if 'data-premium-version=' in source or slug == "machine-learning-notes":
        return source, {"skipped": "already styled or reference page"}
    main = MAIN_RE.search(source)
    if not main:
        return source, {"skipped": "no book-page main"}
    theme = classification(slug, record, source)
    langs = re.search(r'<html\b[^>]*\blang="([^"]+)"', source, re.I)
    lang = (langs.group(1).lower().split("-")[0] if langs else "en")
    changed = source[:main.start()] + main.group(0).replace(
        f'class="{main.group(1)}"',
        f'class="{main.group(1)} premium-book-page theme-{theme}" data-premium-version="{VERSION}"',
        1,
    ) + source[main.end():]

    seen = {}
    def section_replacer(match: re.Match) -> str:
        kind = section_kind(match.group("heading"))
        if not kind or kind in seen:
            return match.group(0)
        attrs = match.group("attrs")
        section_id = f"premium-{kind}"
        if re.search(r'\bid="[^"]+"', attrs):
            section_id = re.search(r'\bid="([^"]+)"', attrs).group(1)
        else:
            attrs += f' id="{section_id}"'
        if 'class="' in attrs:
            attrs = re.sub(r'class="([^"]+)"', lambda m: f'class="{m.group(1)} premium-{kind}"', attrs, count=1)
        else:
            attrs += f' class="section premium-{kind}"'
        seen[kind] = section_id
        return "<section" + attrs + ">" + match.group("gap") + match.group(4) + match.group("heading") + match.group(6)
    changed = HEADING_RE.sub(section_replacer, changed)

    order = ("about", "learning", "topics", "audience", "related")
    nav_label, label_list = NAV_LABELS.get(lang, NAV_LABELS["en"])
    links = [
        f'<a href="#{escape(seen[kind])}">{escape(label_list[i])}</a>'
        for i, kind in enumerate(order) if kind in seen
    ]
    nav = (
        '\n<nav class="premium-toc" aria-label="Book sections"><strong>'
        + escape(nav_label) + "</strong>" + "".join(links) + "</nav>\n"
        if links else ""
    )
    topics = record.get("key_topics") or []
    if not topics:
        topic_list = re.search(r'<section\b[^>]*\bid="premium-topics"[^>]*>(.*?)</section>', changed, re.I | re.S)
        if topic_list:
            topics = [unescape(re.sub(r'<[^>]+>', '', m)).strip() for m in re.findall(r'<li[^>]*>(.*?)</li>', topic_list.group(1), re.I | re.S)]
    chips = []
    for topic in topics:
        value = str(topic).strip()
        if value and len(value) < 62 and value not in chips:
            chips.append(value)
        if len(chips) == 5:
            break
    chip_html = ('<ul class="premium-focus" aria-label="Core themes">' +
                 ''.join(f'<li>{escape(topic)}</li>' for topic in chips) +
                 '</ul>\n') if chips else ""
    changed, hero_count = BOOK_TOP_RE.subn(lambda m: m.group(1) + nav + chip_html, changed, count=1)

    if not re.search(r'<h2[^>]*>\s*(About the author|Yazar hakkında|Sobre el autor|Über den Autor|À propos de l.auteur|Об авторе)', changed, re.I):
        changed = changed.replace("</main>", author_card(lang) + "</main>", 1)
    return changed, {"theme": theme, "sections": sorted(seen), "nav": bool(hero_count), "chips": len(chips)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Audit without writing files")
    args = parser.parse_args()
    completed_path = BOOKS / "completed.json"
    records = json.loads(completed_path.read_text(encoding="utf-8")) if completed_path.exists() else {}
    report = Counter()
    for page in sorted(BOOKS.glob("*/index.html")):
        slug = page.parent.name
        if slug in SKIP:
            continue
        original = page.read_text(encoding="utf-8")
        revised, details = premiumize(original, slug, records.get(slug) or {})
        if revised == original:
            report["unchanged"] += 1
            continue
        before_links, after_links = Counter(LINK_RE.findall(original)), Counter(LINK_RE.findall(revised))
        if any(after_links[url] < count for url, count in before_links.items()):
            raise SystemExit(f"Outbound link or cover reference lost: {page}")
        if revised.count("<h1") != original.count("<h1"):
            raise SystemExit(f"Page title changed: {page}")
        if not args.check:
            page.write_text(revised, encoding="utf-8")
        report["updated"] += 1
        report[f"theme_{details['theme']}"] += 1
        report["with_navigation"] += bool(details["nav"])
        report["with_focus_chips"] += bool(details["chips"])
    print(json.dumps(dict(report), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
