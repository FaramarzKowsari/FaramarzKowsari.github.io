#!/usr/bin/env python3
"""Render Pinterest-hosted visual guides without any outbound Pinterest links.

Pinterest may host the image bytes on i.pinimg.com, but every clickable image and
button routes only to the corresponding Google Play Books purchase page. Direct
Pinterest pin links and Pinterest embed scripts are intentionally forbidden.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
DATA = BOOKS_DIR / "pinterest-infographics.json"
START = "<!-- pinterest-infographics:start -->"
END = "<!-- pinterest-infographics:end -->"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def valid_google_books_url(url: str) -> bool:
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() == "play.google.com"
        and parts.path == "/store/books/details"
        and bool(re.search(r"(?:^|&)id=[A-Za-z0-9_-]+(?:&|$)", parts.query))
    )


def valid_pinimg_url(url: str) -> bool:
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() == "i.pinimg.com"
        and parts.path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )


def render_card(pin, google_url):
    title = esc(pin.get("title") or "Book infographic")
    desc = esc(pin.get("description") or "")
    alt = esc(pin.get("alt_text") or pin.get("title") or "Book infographic")
    image_url = str(pin.get("image_url") or "").strip()

    return f'''    <figure class="pinterest-infographic-card">
      <h3>{title}</h3>
      <a class="pinterest-infographic-image-link" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer" aria-label="View or buy the book on Google Books">
        <img src="{esc(image_url)}" alt="{alt}" title="{title}" loading="lazy" decoding="async">
      </a>
      <figcaption>{desc}</figcaption>
      <div class="pinterest-infographic-actions">
        <a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer">View / Buy on Google Books</a>
      </div>
    </figure>'''


def render_section(config):
    title = esc(config.get("section_title") or "Visual Guides & Infographics")
    intro = esc(config.get("intro") or "")
    google_url = str(config.get("google_books_url") or "").strip()
    pins = config.get("pins") or []
    cards = "\n".join(render_card(pin, google_url) for pin in pins)
    return f'''{START}
<section class="section pinterest-infographics" aria-labelledby="pinterest-infographics-title">
  <style>
    .pinterest-infographics{{margin-top:44px;padding-top:30px}}
    .pinterest-infographics>p{{max-width:820px}}
    .pinterest-infographic-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;margin-top:24px}}
    .pinterest-infographic-card{{margin:0;padding:20px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.05)}}
    .pinterest-infographic-card h3{{margin:0 0 14px;font-size:20px;line-height:1.35}}
    .pinterest-infographic-image-link{{display:block;text-decoration:none}}
    .pinterest-infographic-image-link img{{display:block;width:100%;height:auto;max-height:760px;object-fit:contain;border-radius:14px;border:1px solid var(--line);background:#f3f4f6}}
    .pinterest-infographic-card figcaption{{margin-top:14px;font-size:15px;line-height:1.65;color:var(--muted)}}
    .pinterest-infographic-actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px}}
    .pinterest-infographic-actions .action{{margin:0}}
    @media(max-width:760px){{.pinterest-infographic-grid{{grid-template-columns:1fr}}}}
  </style>
  <h2 id="pinterest-infographics-title">{title}</h2>
  <p>{intro}</p>
  <div class="pinterest-infographic-grid">
{cards}
  </div>
</section>
{END}'''


def replace_or_insert(text, block):
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    if "</main>" in text:
        return text.replace("</main>", block + "\n</main>", 1)
    return text + "\n" + block + "\n"


def remove_legacy_pinterest_script(text: str) -> str:
    return re.sub(
        r'\s*<script\b[^>]*src=["\']https://assets\.pinterest\.com/js/pinit\.js["\'][^>]*></script>\s*',
        "\n",
        text,
        flags=re.I,
    )


def main():
    if not DATA.exists():
        print("No Pinterest infographic data file; nothing to do.")
        return

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("books/pinterest-infographics.json must contain a JSON object")

    errors = []
    updated = 0

    for slug, config in payload.items():
        page = BOOKS_DIR / slug / "index.html"
        if not page.exists():
            errors.append(f"{slug}: missing book page")
            continue

        google_url = str(config.get("google_books_url") or "").strip()
        if not valid_google_books_url(google_url):
            errors.append(f"{slug}: invalid Google Play Books URL")
            continue

        pins = config.get("pins") or []
        if not pins:
            errors.append(f"{slug}: no visual-guide images configured")
            continue

        for index, pin in enumerate(pins, start=1):
            if not isinstance(pin, dict):
                errors.append(f"{slug}: visual guide {index} must be an object")
                continue
            image_url = str(pin.get("image_url") or "").strip()
            if not valid_pinimg_url(image_url):
                errors.append(
                    f"{slug}: visual guide {index} must use a direct i.pinimg.com image URL"
                )
            if pin.get("pin_url"):
                errors.append(
                    f"{slug}: visual guide {index} contains a forbidden Pinterest pin link"
                )

        if errors:
            continue

        text = page.read_text(encoding="utf-8")
        text = remove_legacy_pinterest_script(text)
        block = render_section(config)

        # Hard invariant: Pinterest can host image bytes, but cannot receive clicks.
        if 'href="https://www.pinterest.' in block or 'href="https://i.pinimg.com/' in block:
            errors.append(f"{slug}: rendered visual section contains an outbound Pinterest link")
            continue

        expected_links = len(pins) * 2  # image + Google Books action button
        actual_links = block.count(f'href="{esc(google_url)}"')
        if actual_links != expected_links:
            errors.append(
                f"{slug}: every image and action must link to Google Books "
                f"(expected {expected_links}, found {actual_links})"
            )
            continue

        text = replace_or_insert(text, block)
        page.write_text(text, encoding="utf-8")
        updated += 1

    if errors:
        for item in errors:
            print("ERROR:", item)
        print(f"Pinterest visual-guide layer FAILED with {len(errors)} error(s).")
        sys.exit(1)

    print(
        f"Updated Pinterest-hosted visual sections on {updated} book page(s); "
        "all user clicks route only to Google Play Books."
    )


if __name__ == "__main__":
    main()
