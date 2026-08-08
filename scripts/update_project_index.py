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

def build_sitemap(repos):
    urls = [ROOT_URL]

    for repo in repos:
        if repo.get("has_pages"):
            urls.append(f"{ROOT_URL}{repo['name']}/")

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

    Path("sitemap.xml").write_text(
        build_sitemap(repos),
        encoding="utf-8"
    )

    print(f"Indexed {len(repos)} public non-fork repositories.")
    print(f"Included {sum(1 for r in repos if r.get('has_pages')) + 1} URLs in sitemap.xml.")

if __name__ == "__main__":
    main()
