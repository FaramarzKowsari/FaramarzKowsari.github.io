#!/usr/bin/env python3
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "FaramarzKowsari"
ROOT_REPO = f"{USERNAME}.github.io"
ROOT_URL = f"https://{USERNAME.lower()}.github.io/"
API = f"https://api.github.com/users/{USERNAME}/repos"
TOKEN = os.getenv("GITHUB_TOKEN", "")


def api_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-project-index"
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_repositories():
    repos = []
    page = 1

    while True:
        url = (
            f"{API}?type=owner&sort=updated&direction=desc"
            f"&per_page=100&page={page}"
        )
        batch = api_get(url)
        repos.extend(batch)

        if len(batch) < 100:
            break
        page += 1

    return [
        repo for repo in repos
        if not repo.get("fork") and repo.get("name") != ROOT_REPO
    ]


def project_record(repo):
    return {
        "name": repo.get("name", ""),
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "topics": repo.get("topics") or [],
        "archived": bool(repo.get("archived")),
        "fork": bool(repo.get("fork")),
        "has_pages": bool(repo.get("has_pages")),
        "homepage": repo.get("homepage") or "",
        "html_url": repo.get("html_url") or "",
        "stargazers_count": int(repo.get("stargazers_count") or 0),
        "pushed_at": repo.get("pushed_at") or repo.get("updated_at") or ""
    }


def reviewed_book_slugs():
    """Return all source-reviewed book slugs from the primary and supplemental manifests."""
    slugs = []
    for reviewed_path in (
        Path("books/completed.json"),
        Path("books/source-reviewed-extra.json"),
    ):
        if not reviewed_path.exists():
            continue
        try:
            reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Warning: could not read {reviewed_path}: {exc}")
            continue
        if not isinstance(reviewed, dict):
            print(f"Warning: {reviewed_path} is not a JSON object; skipping it.")
            continue
        for slug in reviewed:
            if isinstance(slug, str) and slug.strip():
                slugs.append(slug.strip('/'))
    return list(dict.fromkeys(slugs))


def completed_book_urls():
    """Return source-reviewed book landing pages that are ready to index."""
    slugs = reviewed_book_slugs()
    if not slugs:
        return []

    urls = [f"{ROOT_URL}books/"]
    urls.extend(f"{ROOT_URL}books/{slug}/" for slug in slugs)
    return urls


def build_sitemap(repos):
    urls = [ROOT_URL]

    for repo in repos:
        if repo.get("has_pages"):
            urls.append(f"{ROOT_URL}{repo['name']}/")

    # The root repository also contains the scalable book library. Only
    # source-reviewed books from the review manifests are added so unfinished
    # placeholder pages remain out of the sitemap until their PDFs are reviewed.
    urls.extend(completed_book_urls())

    # De-duplicate while preserving order.
    urls = list(dict.fromkeys(urls))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for url in urls:
        lines.extend([
            "  <url>",
            f"    <loc>{escape(url)}</loc>",
            "  </url>"
        ])

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    repos = fetch_repositories()

    Path("projects.json").write_text(
        json.dumps(
            [project_record(repo) for repo in repos],
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    sitemap = build_sitemap(repos)
    Path("sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"Indexed {len(repos)} public non-fork repositories.")
    print(f"Included {sitemap.count('<url>')} URLs in sitemap.xml.")


if __name__ == "__main__":
    main()
