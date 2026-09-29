#!/usr/bin/env python3
"""Apply the evergreen Faramarz Kowsari books-library brand image across public entry points.

The repository Social Preview image itself is configured in GitHub Settings by the owner.
This script reuses the same uploaded image on the public website for Open Graph/Twitter
sharing metadata and as a visible, accessible gateway to the Books library.

Use --root-only from the project-hub workflow and --books-only from the Books workflow.
Keeping those scopes separate avoids concurrent workflows leaving unrelated files dirty.
"""

from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
SOCIAL_IMAGE = "https://faramarzkowsari.github.io/books/images/Social%20Preview.jpg"
SOCIAL_ALT = (
    "Faramarz Kowsari Official Website and Multilingual Books Library, featuring "
    "artificial intelligence, trading, data science, business, personal growth and language learning"
)

STYLE = r'''<style id="library-social-preview-style">
.library-brand-banner{width:min(calc(100% - 40px),1180px);margin:34px auto 0;display:block;text-decoration:none;border-radius:24px;overflow:hidden;border:1px solid rgba(52,87,213,.22);background:#081426;box-shadow:0 24px 60px rgba(15,23,42,.18)}
.library-brand-banner img{display:block;width:100%;height:auto;aspect-ratio:2/1;object-fit:cover;background:#081426}
.library-brand-banner:focus-visible{outline:3px solid #0b57d0;outline-offset:4px}
.library-brand-caption{display:block;padding:10px 14px;text-align:center;background:#fff;color:#34415e;font-size:.88rem;font-weight:750;letter-spacing:.01em}
.books-catalog-banner{width:100%;margin:0 0 28px}
.books-catalog-banner .library-brand-caption{background:#fff}
@media(max-width:560px){.library-brand-banner{width:min(calc(100% - 28px),1180px);border-radius:18px}.library-brand-caption{font-size:.82rem;padding:9px 11px}}
@media(prefers-reduced-motion:reduce){.library-brand-banner{scroll-behavior:auto}}
@media(forced-colors:active){.library-brand-banner{forced-color-adjust:auto;border:2px solid CanvasText}}
</style>'''

ROOT_BANNER = f'''<!-- library-social-preview:start -->
<a class="library-brand-banner" href="/books/" aria-label="Open the official multilingual books library of Faramarz Kowsari">
  <img src="/books/images/Social%20Preview.jpg" alt="{SOCIAL_ALT}" loading="lazy" decoding="async">
  <span class="library-brand-caption">Official Website &amp; Multilingual Books Library · Browse the complete collection</span>
</a>
<!-- library-social-preview:end -->'''

BOOKS_BANNER = f'''<!-- library-social-preview:start -->
<a class="library-brand-banner books-catalog-banner" href="./topics/" aria-label="Browse Faramarz Kowsari books by topic">
  <img src="./images/Social%20Preview.jpg" alt="{SOCIAL_ALT}" loading="eager" decoding="async">
  <span class="library-brand-caption">Explore the library by topic, language and interest</span>
</a>
<!-- library-social-preview:end -->'''

START = "<!-- library-social-preview:start -->"
END = "<!-- library-social-preview:end -->"


def replace_or_add_meta(text: str, key: str, value: str, attr: str = "property") -> str:
    pattern = rf'<meta\s+{attr}="{re.escape(key)}"\s+content="[^"]*"\s*/?>'
    replacement = f'<meta {attr}="{key}" content="{value}">'
    if re.search(pattern, text, flags=re.I):
        return re.sub(pattern, replacement, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {replacement}\n</head>", 1)


def ensure_style(text: str) -> str:
    text = re.sub(r'<style id="library-social-preview-style">.*?</style>\s*', "", text, flags=re.S | re.I)
    return text.replace("</head>", STYLE + "\n</head>", 1)


def apply_social_meta(text: str) -> str:
    text = replace_or_add_meta(text, "og:image", SOCIAL_IMAGE, "property")
    text = replace_or_add_meta(text, "og:image:alt", SOCIAL_ALT, "property")
    text = replace_or_add_meta(text, "twitter:card", "summary_large_image", "name")
    text = replace_or_add_meta(text, "twitter:image", SOCIAL_IMAGE, "name")
    text = replace_or_add_meta(text, "twitter:image:alt", SOCIAL_ALT, "name")
    return text


def strip_banner(text: str) -> str:
    return re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', "", text, flags=re.S)


def update_root() -> bool:
    path = ROOT / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    old = text
    text = apply_social_meta(text)
    text = ensure_style(text)
    text = strip_banner(text)
    # Keep the branded image outside the JS-enhanced .container so app.js never replaces it.
    # Do not use a word boundary after the closing quote: both the quote and following space
    # are non-word characters, so that boundary would never match normal HTML.
    section_match = re.search(r'(<section\s+id="books"[^>]*>.*?</section>)', text, flags=re.S | re.I)
    if section_match:
        section = section_match.group(1)
        section = section.rsplit("</section>", 1)[0] + "\n      " + ROOT_BANNER + "\n    </section>"
        text = text[:section_match.start()] + section + text[section_match.end():]
    if text != old:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def update_books_index() -> bool:
    path = ROOT / "books" / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    old = text
    text = apply_social_meta(text)
    text = ensure_style(text)
    text = strip_banner(text)
    text = text.replace('<header class="hero">', '<header class="hero">' + BOOKS_BANNER, 1)
    if text != old:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def update_topics() -> bool:
    path = ROOT / "books" / "topics" / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    old = text
    text = apply_social_meta(text)
    # No duplicate visible banner here: /books/ is the branded visual gateway,
    # while Topics stays optimized for scanning and search.
    if text != old:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--root-only", action="store_true", help="Update only the main website entry page")
    scope.add_argument("--books-only", action="store_true", help="Update only /books/ and /books/topics/")
    args = parser.parse_args()

    changed = []
    if not args.books_only and update_root():
        changed.append("index.html")
    if not args.root_only:
        if update_books_index():
            changed.append("books/index.html")
        if update_topics():
            changed.append("books/topics/index.html")
    print("Social preview branding updated: " + (", ".join(changed) if changed else "no changes needed"))


if __name__ == "__main__":
    main()
