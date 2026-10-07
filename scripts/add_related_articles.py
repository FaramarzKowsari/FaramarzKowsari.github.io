#!/usr/bin/env python3
"""Add durable editorial/article links to selected GitHub Books pages.

Configuration lives in books/related-articles.json. The script injects one
compact visible section and also links the article to the Book JSON-LD using
schema.org subjectOf. It is idempotent and fails if a configured page is missing
or the resulting page does not contain the expected article URL.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
CONFIG = BOOKS / "related-articles.json"
PERSON_ID = "https://faramarzkowsari.github.io/#person"

START = "<!-- related-articles:start -->"
END = "<!-- related-articles:end -->"
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def remove_marked(text: str) -> str:
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END) + r"\s*",
        re.I | re.S,
    )
    return pattern.sub("", text)


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def article_section(items: list[dict]) -> str:
    cards = []
    for item in items:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        platform = str(item.get("platform") or "Article").strip()
        description = str(item.get("description") or "").strip()
        cards.append(
            f'''  <article class="related-article-card">
    <h3>{esc(title)}</h3>
    {f'<p>{esc(description)}</p>' if description else ''}
    <p><a class="action" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Read on {esc(platform)}</a></p>
  </article>'''
        )
    return (
        f"\n{START}\n"
        '<section class="section related-articles" aria-labelledby="related-articles-heading">\n'
        '  <h2 id="related-articles-heading">Featured article</h2>\n'
        '  <p>A companion article by Faramarz Kowsari for readers who want to continue exploring the ideas behind this book.</p>\n'
        + "\n".join(cards)
        + f"\n</section>\n{END}\n"
    )


def is_book(node: dict) -> bool:
    value = node.get("@type")
    if isinstance(value, list):
        return "Book" in value
    return value == "Book"


def patch_book_subject_of(text: str, items: list[dict]) -> tuple[str, bool]:
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        raw = match.group(2).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)

        nodes = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes = [x for x in payload["@graph"] if isinstance(x, dict)]
        elif isinstance(payload, dict):
            nodes = [payload]

        book = next((node for node in nodes if is_book(node)), None)
        if not book:
            return match.group(0)

        existing = book.get("subjectOf")
        if isinstance(existing, dict):
            existing = [existing]
        if not isinstance(existing, list):
            existing = []

        configured_urls = {str(item.get("url") or "").strip() for item in items}
        existing = [
            item for item in existing
            if not (isinstance(item, dict) and str(item.get("url") or "").strip() in configured_urls)
        ]

        additions = []
        for item in items:
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            platform = str(item.get("platform") or "").strip()
            article = {
                "@type": "Article",
                "headline": title,
                "url": url,
                "author": {"@id": PERSON_ID},
            }
            if platform:
                article["publisher"] = {"@type": "Organization", "name": platform}
            additions.append(article)

        book["subjectOf"] = existing + additions
        changed = True
        return match.group(1) + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + match.group(3)

    return SCRIPT_RE.sub(repl, text), changed


def main() -> None:
    config = load_json(CONFIG, {})
    if not isinstance(config, dict):
        raise SystemExit("books/related-articles.json must be a JSON object")

    errors = []
    updated = 0

    for slug, raw_items in config.items():
        items = [item for item in (raw_items or []) if isinstance(item, dict)]
        if not items:
            continue

        for item in items:
            if not str(item.get("title") or "").strip() or not str(item.get("url") or "").strip():
                errors.append(f"{slug}: each related article requires title and url")

        page = BOOKS / slug / "index.html"
        if not page.exists():
            errors.append(f"{slug}: configured book page does not exist")
            continue

        text = page.read_text(encoding="utf-8")
        text = remove_marked(text)
        text, schema_changed = patch_book_subject_of(text, items)
        if not schema_changed:
            errors.append(f"{slug}: Book JSON-LD not found for article relationship")

        section = article_section(items)
        if "<!-- pinterest-infographics:start -->" in text:
            text = text.replace("<!-- pinterest-infographics:start -->", section + "\n<!-- pinterest-infographics:start -->", 1)
        elif "</main>" in text:
            text = text.replace("</main>", section + "\n</main>", 1)
        else:
            errors.append(f"{slug}: could not find insertion point")
            continue

        for item in items:
            url = str(item.get("url") or "").strip()
            if text.count(url) < 2:
                errors.append(f"{slug}: article URL was not linked in both visible HTML and Book JSON-LD: {url}")

        if text.count(START) != 1 or text.count(END) != 1:
            errors.append(f"{slug}: related-article marker duplication detected")

        page.write_text(text, encoding="utf-8")
        updated += 1

    if errors:
        for error in errors:
            print("ERROR:", error)
        print(f"Related-article layer FAILED with {len(errors)} error(s).")
        sys.exit(1)

    print(f"Related-article layer applied to {updated} book page(s).")


if __name__ == "__main__":
    main()
