#!/usr/bin/env python3
"""Submit newly changed public URLs to IndexNow.

Designed for GitHub Pages. The IndexNow key file is intentionally public at the
site root, as required by the protocol. Only URLs on faramarzkowsari.github.io
are submitted.
"""

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOST = "faramarzkowsari.github.io"
BASE = f"https://{HOST}/"
KEY = "9b98e167b32cad1462454e76dd029a61"
KEY_FILE = ROOT / f"{KEY}.txt"
KEY_LOCATION = f"{BASE}{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def git_changed_files(before: str, after: str):
    before = (before or "").strip()
    after = (after or "").strip()
    zeros = "0" * 40
    try:
        if not after:
            after = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if not before or before == zeros:
            before = subprocess.check_output(["git", "rev-parse", f"{after}^"], cwd=ROOT, text=True).strip()
        out = subprocess.check_output(
            ["git", "diff", "--name-only", before, after], cwd=ROOT, text=True
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception as exc:
        print(f"Could not determine changed files: {exc}")
        return []


def public_url_for_path(path: str):
    path = path.replace("\\", "/").lstrip("./")

    if path == "index.html":
        return BASE
    if path == "books/index.html":
        return BASE + "books/"
    if path == "books/all-books/index.html":
        return BASE + "books/all-books/"
    if path == "books/author/index.html":
        return BASE + "books/author/"
    if path == "books/topics/index.html":
        return BASE + "books/topics/"
    if path.startswith("books/") and path.endswith("/index.html"):
        parts = path.split("/")
        if len(parts) == 3:
            return BASE + f"books/{parts[1]}/"

    # Public discovery resources can be submitted as URLs as well.
    if path in {"llms.txt", "sitemap.xml", "robots.txt", f"{KEY}.txt"}:
        return BASE + path
    if path in {"books/sitemap.xml", "books/catalog.json"}:
        return BASE + path

    return None


def collect_urls(changed):
    urls = []
    seen = set()
    for path in changed:
        url = public_url_for_path(path)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    # When infrastructure changes but no directly mapped public page changed,
    # notify IndexNow about the principal discovery hubs once.
    if not urls:
        urls = [
            BASE,
            BASE + "books/",
            BASE + "books/all-books/",
            BASE + "books/author/",
            BASE + "books/topics/",
        ]
    return urls[:10000]


def submit(urls):
    if not KEY_FILE.exists() or KEY_FILE.read_text(encoding="utf-8").strip() != KEY:
        raise SystemExit("IndexNow key file is missing or invalid.")

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "FaramarzKowsari-GitHubPages-IndexNow/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"IndexNow response: HTTP {resp.status}")
            if body:
                print(body)
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"IndexNow HTTP error: {exc.code} {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"IndexNow submission failed: {exc}", file=sys.stderr)
        return 1


def main():
    before = os.environ.get("INDEXNOW_BEFORE", "")
    after = os.environ.get("INDEXNOW_AFTER", "")
    changed = git_changed_files(before, after)
    urls = collect_urls(changed)
    print(f"Submitting {len(urls)} URL(s) to IndexNow:")
    for url in urls:
        print(f" - {url}")
    raise SystemExit(submit(urls))


if __name__ == "__main__":
    main()
