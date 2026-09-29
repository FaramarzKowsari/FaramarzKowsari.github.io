#!/usr/bin/env python3
"""Idempotent WCAG 2.2 AA-oriented accessibility hardening for the root hub."""

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
APP = ROOT / "app.js"


def add_section_label(text, section_id, heading_text, heading_id):
    section_pattern = rf'(<section\b[^>]*\bid=["\']{re.escape(section_id)}["\'][^>]*)>'
    text = re.sub(
        section_pattern,
        lambda m: m.group(0) if "aria-labelledby=" in m.group(0) else m.group(1) + f' aria-labelledby="{heading_id}">',
        text,
        count=1,
        flags=re.I,
    )
    heading_pattern = rf'<h2(?:\s+id=["\']{re.escape(heading_id)}["\'])?>(\s*{re.escape(heading_text)}\s*)</h2>'
    text = re.sub(heading_pattern, rf'<h2 id="{heading_id}">\1</h2>', text, count=1, flags=re.I)
    return text


def label_project_links(text):
    pattern = re.compile(r'(<article class="project-card(?: featured)?">)(.*?)(</article>)', re.S)

    def repl(match):
        block = match.group(0)
        h = re.search(r'<h3>(.*?)</h3>', block, re.S)
        if not h:
            return block
        title = re.sub(r'<[^>]+>', ' ', h.group(1))
        title = html.unescape(re.sub(r'\s+', ' ', title)).strip()
        safe = html.escape(title, quote=True)
        block = re.sub(
            r'<a href="([^"]+)"(?:\s+aria-label="[^"]*")?>Live site\s*→</a>',
            rf'<a href="\1" aria-label="Open live site for {safe}">Live site →</a>',
            block,
            count=1,
        )
        block = re.sub(
            r'<a href="([^"]+)"(?:\s+aria-label="[^"]*")?>Repository</a>',
            rf'<a href="\1" aria-label="Open GitHub repository for {safe}">Repository</a>',
            block,
            count=1,
        )
        return block

    return pattern.sub(repl, text)


def update_index():
    text = INDEX.read_text(encoding="utf-8")
    original = text

    # Normalize the hidden GTM iframe to one canonical accessible opening tag.
    # This intentionally collapses any duplicate accessibility attributes left by older runs.
    text = re.sub(
        r'<iframe\s+src="https://www\.googletagmanager\.com/ns\.html\?id=GTM-5G888PFF"(?:\s+(?:title="Google Tag Manager"|aria-hidden="true"|tabindex="-1"))*',
        '<iframe src="https://www.googletagmanager.com/ns.html?id=GTM-5G888PFF" title="Google Tag Manager" aria-hidden="true" tabindex="-1"',
        text,
        count=1,
        flags=re.I,
    )

    # Social image alternatives help link-preview systems understand the image purpose.
    if 'property="og:image:alt"' not in text:
        text = text.replace(
            '<meta property="og:image" content="https://github.com/FaramarzKowsari.png">',
            '<meta property="og:image" content="https://github.com/FaramarzKowsari.png">\n  <meta property="og:image:alt" content="Portrait of Faramarz Kowsari, author, software engineer and AI researcher">',
            1,
        )
    if 'name="twitter:image:alt"' not in text:
        text = text.replace(
            '<meta name="twitter:image" content="https://github.com/FaramarzKowsari.png">',
            '<meta name="twitter:image" content="https://github.com/FaramarzKowsari.png">\n  <meta name="twitter:image:alt" content="Portrait of Faramarz Kowsari, author, software engineer and AI researcher">',
            1,
        )

    # The homepage currently has one meaningful content image: the author portrait.
    text = text.replace(
        'alt="Portrait of Faramarz Kowsari"',
        'alt="Portrait photograph of Faramarz Kowsari, author, software engineer and AI researcher"'
    )
    text = re.sub(
        r'width="360" height="360"(?:\s+loading="eager")?(?:\s+decoding="async")?>',
        'width="360" height="360" loading="eager" decoding="async">',
        text,
        count=1,
    )

    # Make the skip-link destination focusable and associate major regions with headings.
    text = re.sub(r'<main id="main"(?:\s+tabindex="-1")?>', '<main id="main" tabindex="-1">', text, count=1)
    text = re.sub(
        r'<section class="hero container"(?:\s+aria-labelledby="page-title")?>',
        '<section class="hero container" aria-labelledby="page-title">',
        text,
        count=1,
    )
    text = re.sub(r'<h1(?:\s+id="page-title")?>Faramarz Kowsari</h1>', '<h1 id="page-title">Faramarz Kowsari</h1>', text, count=1)
    text = add_section_label(text, "about", "A permanent home for a growing body of work", "about-title")
    text = add_section_label(text, "project-sites", "Project sites", "project-sites-title")
    text = add_section_label(text, "repositories", "All public repositories", "repositories-title")
    text = add_section_label(text, "profiles", "Official profiles", "profiles-title")
    text = add_section_label(text, "books", "Books by Faramarz Kowsari", "books-title")

    # Normalize live regions so only compact status text is announced.
    text = re.sub(
        r'id="repo-count"(?:\s+role="status")?(?:\s+aria-live="polite")?(?:\s+aria-atomic="true")?',
        'id="repo-count" role="status" aria-live="polite" aria-atomic="true"',
        text,
        count=1,
    )
    text = re.sub(
        r'id="repo-status" class="notice" role="status"(?:\s+aria-live="polite")?(?:\s+aria-atomic="true")?',
        'id="repo-status" class="notice" role="status" aria-live="polite" aria-atomic="true"',
        text,
        count=1,
    )
    text = re.sub(
        r'id="repo-grid" class="project-grid dynamic-projects"(?:\s+aria-live="polite")?(?:\s+aria-describedby="repo-count")?',
        'id="repo-grid" class="project-grid dynamic-projects" aria-describedby="repo-count"',
        text,
        count=1,
    )

    text = label_project_links(text)

    if text != original:
        INDEX.write_text(text, encoding="utf-8")
        return True
    return False


def update_app():
    if not APP.exists():
        return False
    text = APP.read_text(encoding="utf-8")
    original = text

    # Repeated link labels in dynamically generated repository cards get unique accessible names.
    text = text.replace(
        '${live ? `<a href="${escapeHtml(live)}">Live site →</a>` : ""}',
        '${live ? `<a href="${escapeHtml(live)}" aria-label="Open live site for ${escapeHtml(prettyName(repo.name))}">Live site →</a>` : ""}'
    )
    text = text.replace(
        '<a href="${escapeHtml(repo.html_url)}">Repository</a>',
        '<a href="${escapeHtml(repo.html_url)}" aria-label="Open GitHub repository for ${escapeHtml(prettyName(repo.name))}">Repository</a>'
    )

    if text != original:
        APP.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    changed = []
    if update_index():
        changed.append("index.html")
    if update_app():
        changed.append("app.js")
    print("WCAG root hardening updated: " + (", ".join(changed) if changed else "no changes needed"))


if __name__ == "__main__":
    main()
