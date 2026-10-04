#!/usr/bin/env python3
"""Add a durable free-companion callout to every IELTS SOS book page.

The rule is title-based and future-facing: any individual book page whose H1
contains "IELTS SOS" receives a localized callout for the free visual companion.
The companion page itself is excluded. Because this runs after localized landing
pages are generated, the relationship appears on the original book page and on
all generated discovery-language pages as well.

This is a text-only post-processing step. It does not download or store images.
"""
from __future__ import annotations

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"

COMPANION_SLUG = "free-ielts-sos-visual-companion"
COMPANION_PAGE = f"https://faramarzkowsari.github.io/books/{COMPANION_SLUG}/"
COMPANION_GOOGLE = "https://play.google.com/store/books/details?id=2P0VEgAAQBAJ"
COMPANION_TITLE = "FREE IELTS SOS Visual Companion"
COMPANION_SUBTITLE = "90-Minute Graphic Review for Listening, Reading, Writing & Speaking"

START = "<!-- ielts-sos-free-companion:start -->"
END = "<!-- ielts-sos-free-companion:end -->"

H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.I)
TAG_RE = re.compile(r"<[^>]+>")
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.S)

COPY = {
    "en": {
        "heading": "FREE visual companion for the IELTS SOS series",
        "body": "This IELTS SOS edition has a free visual companion on Google Books. Use it as a 90-minute graphic review of Listening, Reading, Writing and Speaking for rapid recall before the exam. It complements the full IELTS SOS guide rather than replacing it.",
        "google": "Open the FREE visual companion on Google Books",
        "details": "View companion details",
    },
    "ru": {
        "heading": "БЕСПЛАТНОЕ визуальное дополнение к серии IELTS SOS",
        "body": "К этой книге IELTS SOS доступно бесплатное визуальное дополнение в Google Books: 90-минутный графический обзор Listening, Reading, Writing и Speaking для быстрого повторения перед экзаменом. Оно дополняет основное руководство IELTS SOS, а не заменяет его.",
        "google": "Открыть БЕСПЛАТНОЕ дополнение в Google Books",
        "details": "Страница визуального дополнения",
    },
    "tr": {
        "heading": "IELTS SOS serisi için ÜCRETSİZ görsel tamamlayıcı",
        "body": "Bu IELTS SOS kitabının Google Books'ta ücretsiz bir görsel tamamlayıcısı vardır. Listening, Reading, Writing ve Speaking için 90 dakikalık grafik tekrar olarak, sınavdan önce hızlı hatırlama amacıyla tasarlanmıştır. Ana IELTS SOS rehberini tamamlar; onun yerine geçmez.",
        "google": "ÜCRETSİZ görsel tamamlayıcıyı Google Books'ta aç",
        "details": "Tamamlayıcı kitap sayfasını görüntüle",
    },
    "de": {
        "heading": "KOSTENLOSES visuelles Begleitbuch zur IELTS-SOS-Reihe",
        "body": "Zu dieser IELTS-SOS-Ausgabe gibt es bei Google Books ein kostenloses visuelles Begleitbuch. Es bietet eine 90-minütige grafische Wiederholung zu Listening, Reading, Writing und Speaking für die schnelle Auffrischung vor der Prüfung. Es ergänzt den vollständigen IELTS-SOS-Leitfaden und ersetzt ihn nicht.",
        "google": "KOSTENLOSES Begleitbuch bei Google Books öffnen",
        "details": "Details zum Begleitbuch ansehen",
    },
    "es": {
        "heading": "Complemento visual GRATUITO para la serie IELTS SOS",
        "body": "Esta edición de IELTS SOS tiene un complemento visual gratuito en Google Books. Úsalo como un repaso gráfico de 90 minutos de Listening, Reading, Writing y Speaking para una revisión rápida antes del examen. Complementa la guía completa IELTS SOS; no la sustituye.",
        "google": "Abrir el complemento GRATUITO en Google Books",
        "details": "Ver detalles del complemento",
    },
    "fr": {
        "heading": "Complément visuel GRATUIT pour la série IELTS SOS",
        "body": "Cette édition IELTS SOS dispose d'un complément visuel gratuit sur Google Books. Il propose une révision graphique de 90 minutes de Listening, Reading, Writing et Speaking pour un rappel rapide avant l'examen. Il complète le guide IELTS SOS intégral sans le remplacer.",
        "google": "Ouvrir le complément GRATUIT sur Google Books",
        "details": "Voir les détails du complément",
    },
    "pt-br": {
        "heading": "Companion visual GRATUITO para a série IELTS SOS",
        "body": "Esta edição do IELTS SOS tem um companion visual gratuito no Google Books. Use-o como uma revisão gráfica de 90 minutos de Listening, Reading, Writing e Speaking para uma recapitulação rápida antes da prova. Ele complementa o guia IELTS SOS completo, sem substituí-lo.",
        "google": "Abrir o companion GRATUITO no Google Books",
        "details": "Ver detalhes do companion",
    },
    "id": {
        "heading": "Pendamping visual GRATIS untuk seri IELTS SOS",
        "body": "Edisi IELTS SOS ini memiliki pendamping visual gratis di Google Books. Gunakan sebagai ulasan grafis 90 menit untuk Listening, Reading, Writing, dan Speaking agar dapat mengingat poin penting dengan cepat sebelum ujian. Buku ini melengkapi panduan IELTS SOS utama, bukan menggantikannya.",
        "google": "Buka pendamping visual GRATIS di Google Books",
        "details": "Lihat detail buku pendamping",
    },
    "vi": {
        "heading": "Tài liệu trực quan MIỄN PHÍ cho bộ IELTS SOS",
        "body": "Ấn bản IELTS SOS này có tài liệu trực quan miễn phí trên Google Books. Hãy dùng nó như phần ôn tập đồ họa 90 phút cho Listening, Reading, Writing và Speaking để gợi nhớ nhanh trước kỳ thi. Tài liệu này bổ trợ cho sách IELTS SOS đầy đủ chứ không thay thế sách chính.",
        "google": "Mở tài liệu MIỄN PHÍ trên Google Books",
        "details": "Xem chi tiết tài liệu bổ trợ",
    },
    "ar": {
        "heading": "الملحق البصري المجاني لسلسلة IELTS SOS",
        "body": "لهذه النسخة من IELTS SOS ملحق بصري مجاني على Google Books. استخدمه كمراجعة رسومية لمدة 90 دقيقة لأقسام Listening وReading وWriting وSpeaking لتثبيت أهم النقاط بسرعة قبل الاختبار. وهو مكمل لدليل IELTS SOS الكامل وليس بديلاً عنه.",
        "google": "افتح الملحق المجاني على Google Books",
        "details": "عرض تفاصيل الكتاب المكمل",
    },
    "th": {
        "heading": "คู่มือภาพเสริม IELTS SOS ฟรี",
        "body": "IELTS SOS เล่มนี้มีคู่มือภาพเสริมฟรีบน Google Books ใช้เป็นการทบทวนแบบกราฟิก 90 นาทีสำหรับ Listening, Reading, Writing และ Speaking เพื่อทบทวนประเด็นสำคัญอย่างรวดเร็วก่อนสอบ คู่มือนี้เป็นส่วนเสริมของ IELTS SOS ฉบับเต็ม ไม่ได้ใช้แทนหนังสือหลัก",
        "google": "เปิดคู่มือภาพเสริมฟรีบน Google Books",
        "details": "ดูรายละเอียดหนังสือเสริม",
    },
    "bn": {
        "heading": "IELTS SOS সিরিজের বিনামূল্যের ভিজ্যুয়াল কম্প্যানিয়ন",
        "body": "এই IELTS SOS সংস্করণের জন্য Google Books-এ একটি বিনামূল্যের ভিজ্যুয়াল কম্প্যানিয়ন রয়েছে। Listening, Reading, Writing এবং Speaking-এর গুরুত্বপূর্ণ বিষয় দ্রুত মনে ঝালিয়ে নিতে পরীক্ষার আগে ৯০ মিনিটের গ্রাফিক রিভিউ হিসেবে এটি ব্যবহার করুন। এটি পূর্ণ IELTS SOS গাইডের পরিপূরক, বিকল্প নয়।",
        "google": "Google Books-এ বিনামূল্যের কম্প্যানিয়ন খুলুন",
        "details": "কম্প্যানিয়ন বইয়ের বিস্তারিত দেখুন",
    },
    "fa": {
        "heading": "مکمل ویژوال رایگان برای مجموعه IELTS SOS",
        "body": "برای این نسخه از IELTS SOS یک کتاب مکمل ویژوال رایگان در Google Books وجود دارد. این کتاب یک مرور گرافیکی ۹۰ دقیقه‌ای برای Listening، Reading، Writing و Speaking است تا نکات مهم را پیش از آزمون سریع مرور کنید. این کتاب مکمل راهنمای کامل IELTS SOS است و جای آن را نمی‌گیرد.",
        "google": "باز کردن مکمل رایگان در Google Books",
        "details": "مشاهده صفحه کتاب مکمل",
    },
}


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", fragment))).strip()


def page_title(text: str) -> str:
    match = H1_RE.search(text)
    return plain_text(match.group(1)) if match else ""


def page_lang(text: str) -> str:
    match = HTML_LANG_RE.search(text)
    raw = (match.group(1) if match else "en").strip().lower().replace("_", "-")
    if raw.startswith("pt"):
        return "pt-br"
    primary = raw.split("-", 1)[0]
    return primary if primary in COPY else "en"


def callout(lang: str) -> str:
    strings = COPY.get(lang, COPY["en"])
    rtl = ' dir="rtl"' if lang in {"ar", "fa"} else ""
    return f'''{START}
<section class="section ielts-sos-free-companion" aria-labelledby="ielts-sos-free-companion-title"{rtl}>
  <p><strong>FREE · IELTS SOS VISUAL COMPANION</strong></p>
  <h2 id="ielts-sos-free-companion-title">{html.escape(strings["heading"])}</h2>
  <p>{html.escape(strings["body"])}</p>
  <p><strong>{html.escape(COMPANION_TITLE)}</strong><br>{html.escape(COMPANION_SUBTITLE)}</p>
  <p><a href="{COMPANION_GOOGLE}" target="_blank" rel="noopener noreferrer"><strong>{html.escape(strings["google"])}</strong></a></p>
  <p><a href="{COMPANION_PAGE}">{html.escape(strings["details"])}</a></p>
</section>
{END}
'''


def insert_after_lead_section(text: str, block: str) -> str:
    for class_name in ("book-top", "hero"):
        pattern = re.compile(
            rf'(<section\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>.*?</section>)',
            re.I | re.S,
        )
        match = pattern.search(text)
        if match:
            return text[: match.end()] + "\n" + block + text[match.end() :]
    pos = text.lower().rfind("</main>")
    if pos >= 0:
        return text[:pos] + block + text[pos:]
    return text + "\n" + block


def main() -> None:
    changed = 0
    matched = 0
    for path in sorted(BOOKS.rglob("index.html")):
        if COMPANION_SLUG in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        title = page_title(text)
        if "ielts sos" not in title.lower():
            continue
        matched += 1
        clean = BLOCK_RE.sub("", text)
        updated = insert_after_lead_section(clean, callout(page_lang(clean)))
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"IELTS SOS free visual companion: {matched} page(s) matched; {changed} file(s) updated.")


if __name__ == "__main__":
    main()
