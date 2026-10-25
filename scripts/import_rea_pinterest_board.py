#!/usr/bin/env python3
"""Import the latest REA visual pins from a public Pinterest board.

The script stores only Pinterest CDN image URLs in books/book-image-galleries.json.
It does not download, proxy, cache, or self-host image bytes. Gallery clicks are
kept on the REVERSE ENGINEERING WITH REA Google Play Books page.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "books" / "book-image-galleries.json"

BOARD_URL = "https://www.pinterest.com/faramarzkowsari/faramarz-kowsari-ai-books/"
FEED_URL = BOARD_URL.rstrip("/") + ".rss"
SLUG = "reverse-engineering-with-rea"
CLICK_URL = "https://play.google.com/store/books/details?id=XnUhEgAAQBAJ"
IMAGE_COUNT = 10

PINIMG_RE = re.compile(
    r'https://i\.pinimg\.com/[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
    re.I,
)
REA_HINT_RE = re.compile(r'(?:reverse\s+engineering|\bREA\b)', re.I)


def request_bytes(url: str, *, accept: str = "*/*", timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; FaramarzKowsari-GitHubBooks/1.0)",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def direct_rss_items() -> list[dict[str, str]]:
    raw = request_bytes(FEED_URL, accept="application/rss+xml, application/xml, text/xml, */*")
    root = ET.fromstring(raw)
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        fields: dict[str, str] = {}
        for child in list(item):
            tag = child.tag.rsplit("}", 1)[-1].lower()
            value = child.text or ""
            if tag in {"title", "description", "encoded", "content", "link"}:
                fields[tag] = fields.get(tag, "") + "\n" + value
            for attr_name in ("url", "src"):
                attr_value = child.attrib.get(attr_name)
                if attr_value:
                    fields["media"] = fields.get("media", "") + "\n" + attr_value
        items.append(fields)
    if not items:
        raise RuntimeError("Pinterest RSS returned no items.")
    return items


def rss2json_items() -> list[dict[str, str]]:
    endpoint = (
        "https://api.rss2json.com/v1/api.json?rss_url="
        + urllib.parse.quote(FEED_URL, safe="")
    )
    payload = json.loads(request_bytes(endpoint, accept="application/json").decode("utf-8"))
    if payload.get("status") != "ok":
        raise RuntimeError(f"rss2json error: {payload.get('message') or payload.get('status')}")
    items = []
    for item in payload.get("items") or []:
        items.append(
            {
                "title": str(item.get("title") or ""),
                "description": str(item.get("description") or ""),
                "content": str(item.get("content") or ""),
                "thumbnail": str(item.get("thumbnail") or ""),
                "link": str(item.get("link") or ""),
            }
        )
    if not items:
        raise RuntimeError("rss2json returned no items.")
    return items


def get_items() -> list[dict[str, str]]:
    errors = []
    for loader in (direct_rss_items, rss2json_items):
        try:
            items = loader()
            print(f"Loaded {len(items)} Pinterest board item(s) using {loader.__name__}.")
            return items
        except Exception as exc:  # noqa: BLE001 - fallback is intentional
            errors.append(f"{loader.__name__}: {exc}")
    raise RuntimeError("Could not read Pinterest board feed. " + " | ".join(errors))


def pinimg_urls(text: str) -> list[str]:
    cleaned = html.unescape(text or "")
    urls = []
    for match in PINIMG_RE.findall(cleaned):
        url = match.rstrip(").,;")
        if url not in urls:
            urls.append(url)
    return urls


def upgrade_candidates(url: str) -> list[str]:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path
    candidates = []
    # Pinterest CDN commonly exposes identical content under multiple size paths.
    for size in ("1200x", "736x"):
        upgraded = re.sub(r"^/(?:\d+x|originals)/", f"/{size}/", path, count=1)
        candidate = urllib.parse.urlunsplit(("https", "i.pinimg.com", upgraded, "", ""))
        if candidate not in candidates:
            candidates.append(candidate)
    clean_original = urllib.parse.urlunsplit(("https", "i.pinimg.com", path, "", ""))
    if clean_original not in candidates:
        candidates.append(clean_original)
    return candidates


def image_is_live(url: str) -> bool:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; FaramarzKowsari-GitHubBooks/1.0)",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Range": "bytes=0-1023",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            ctype = (response.headers.get("Content-Type") or "").lower()
            response.read(1)
            return response.status in (200, 206) and ctype.startswith("image/")
    except Exception:
        return False


def choose_image(url: str) -> str:
    for candidate in upgrade_candidates(url):
        if image_is_live(candidate):
            return candidate
    raise RuntimeError(f"No live Pinterest CDN variant found for {url}")


def collect_images(items: list[dict[str, str]]) -> list[str]:
    rows = []
    for index, item in enumerate(items):
        combined = "\n".join(str(v or "") for v in item.values())
        urls = pinimg_urls(combined)
        if not urls:
            continue
        rows.append(
            {
                "index": index,
                "title": str(item.get("title") or "").strip(),
                "match": bool(REA_HINT_RE.search(combined)),
                "url": urls[0],
            }
        )

    if not rows:
        raise RuntimeError("No i.pinimg.com images were found in the Pinterest feed.")

    matching = [row for row in rows if row["match"]]
    source_rows = matching if len(matching) >= IMAGE_COUNT else rows

    selected: list[str] = []
    seen_fingerprints = set()
    for row in source_rows:
        parsed = urllib.parse.urlsplit(row["url"])
        fingerprint = parsed.path.rsplit("/", 1)[-1].lower()
        if fingerprint in seen_fingerprints:
            continue
        resolved = choose_image(row["url"])
        seen_fingerprints.add(fingerprint)
        selected.append(resolved)
        print(f"Selected pin image {len(selected):02d}: {resolved} | {row['title'][:120]}")
        if len(selected) == IMAGE_COUNT:
            break

    if len(selected) != IMAGE_COUNT:
        raise RuntimeError(
            f"Expected {IMAGE_COUNT} unique live Pinterest images but found {len(selected)}."
        )
    return selected


def update_config(images: list[str]) -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    if not isinstance(payload, dict):
        raise RuntimeError("books/book-image-galleries.json must contain a JSON object.")

    payload[SLUG] = {
        "images": images,
        "click_url": CLICK_URL,
    }
    CONFIG.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    items = get_items()
    images = collect_images(items)
    update_config(images)
    print(
        f"Updated {CONFIG.relative_to(ROOT)} with {len(images)} externally hosted "
        f"Pinterest images for {SLUG}; click target is Google Play Books."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
