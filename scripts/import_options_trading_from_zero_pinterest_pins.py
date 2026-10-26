#!/usr/bin/env python3
"""Import the exact Pinterest pins for OPTIONS TRADING FROM ZERO.

Stores only live i.pinimg.com image URLs in books/book-image-galleries.json.
Gallery clicks are routed to the Google Play Books page by the existing renderer.
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
SLUG = "options-trading-from-zero"
CLICK_URL = "https://play.google.com/store/books/details?id=d-khEgAAQBAJ"
PIN_IDS = [
    "729512839687766327",
    "729512839687766329",
    "729512839687766332",
    "729512839687766337",
    "729512839687766339",
    "729512839687766341",
    "729512839687766345",
    "729512839687766346",
    "729512839687766350",
    "729512839687766351",
    "729512839687766354",
]

PINIMG_RE = re.compile(
    r'https://i\.pinimg\.com/[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
    re.I,
)

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
    return items

def rss2json_items() -> list[dict[str, str]]:
    endpoint = "https://api.rss2json.com/v1/api.json?rss_url=" + urllib.parse.quote(FEED_URL, safe="")
    payload = json.loads(request_bytes(endpoint, accept="application/json").decode("utf-8"))
    if payload.get("status") != "ok":
        raise RuntimeError(f"rss2json error: {payload.get('message') or payload.get('status')}")
    return [
        {
            "title": str(item.get("title") or ""),
            "description": str(item.get("description") or ""),
            "content": str(item.get("content") or ""),
            "thumbnail": str(item.get("thumbnail") or ""),
            "link": str(item.get("link") or ""),
        }
        for item in (payload.get("items") or [])
    ]

def get_feed_items() -> list[dict[str, str]]:
    errors = []
    for loader in (direct_rss_items, rss2json_items):
        try:
            items = loader()
            if items:
                print(f"Loaded {len(items)} Pinterest feed item(s) using {loader.__name__}.")
                return items
        except Exception as exc:
            errors.append(f"{loader.__name__}: {exc}")
    raise RuntimeError("Could not read Pinterest feed. " + " | ".join(errors))

def pinimg_urls(text: str) -> list[str]:
    cleaned = html.unescape(text or "")
    out: list[str] = []
    for match in PINIMG_RE.findall(cleaned):
        url = match.rstrip(").,;")
        if url not in out:
            out.append(url)
    return out

def upgrade_candidates(url: str) -> list[str]:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path
    candidates: list[str] = []
    for size in ("1200x", "736x"):
        upgraded = re.sub(r"^/(?:\d+x|originals)/", f"/{size}/", path, count=1)
        candidate = urllib.parse.urlunsplit(("https", "i.pinimg.com", upgraded, "", ""))
        if candidate not in candidates:
            candidates.append(candidate)
    clean = urllib.parse.urlunsplit(("https", "i.pinimg.com", path, "", ""))
    if clean not in candidates:
        candidates.append(clean)
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

META_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\\\'](?:og:image|twitter:image)["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']',
    re.I,
)
META_IMAGE_RE_REVERSED = re.compile(
    r'<meta[^>]+content=["\\\']([^"\\\']+)["\\\'][^>]+(?:property|name)=["\\\'](?:og:image|twitter:image)["\\\']',
    re.I,
)

def direct_pin_candidates(pin_id: str) -> list[str]:
    url = f"https://www.pinterest.com/pin/{pin_id}/"
    raw = request_bytes(url, accept="text/html,application/xhtml+xml,*/*").decode("utf-8", "ignore")
    decoded = html.unescape(raw)

    preferred: list[str] = []
    for pattern in (META_IMAGE_RE, META_IMAGE_RE_REVERSED):
        for match in pattern.findall(decoded):
            value = html.unescape(match).replace("\\/","/")
            if value.startswith("https://i.pinimg.com/") and value not in preferred:
                preferred.append(value)

    for value in pinimg_urls(decoded):
        if value not in preferred:
            preferred.append(value)
    return preferred

def resolve_pin(pin_id: str, items: list[dict[str, str]]) -> str:
    # Prefer an exact RSS item link if Pinterest exposes the pin ID there.
    for item in items:
        link = str(item.get("link") or "")
        if pin_id in link:
            combined = "\n".join(str(v or "") for v in item.values())
            urls = pinimg_urls(combined)
            for url in urls:
                try:
                    return choose_image(url)
                except Exception:
                    continue

    # The individual pin page exposes the canonical visual via og:image/twitter:image.
    try:
        urls = direct_pin_candidates(pin_id)
        for url in urls:
            try:
                return choose_image(url)
            except Exception:
                continue
    except Exception as exc:
        print(f"Direct pin fallback failed for {pin_id}: {exc}")

    # Last resort: search the full RSS item content for the pin ID.
    for item in items:
        combined = "\n".join(str(v or "") for v in item.values())
        if pin_id in combined:
            for url in pinimg_urls(combined):
                try:
                    return choose_image(url)
                except Exception:
                    continue

    raise RuntimeError(f"Could not resolve Pinterest image for pin {pin_id}")

def update_config(images: list[str]) -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    if not isinstance(payload, dict):
        raise RuntimeError("books/book-image-galleries.json must contain a JSON object.")
    payload[SLUG] = {"images": images, "click_url": CLICK_URL}
    CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> None:
    items = get_feed_items()
    images: list[str] = []
    for pin_id in PIN_IDS:
        image = resolve_pin(pin_id, items)
        if image in images:
            raise RuntimeError(f"Duplicate Pinterest image resolved for pin {pin_id}: {image}")
        images.append(image)
        print(f"Resolved {pin_id} -> {image}")
    if len(images) != len(PIN_IDS):
        raise RuntimeError(f"Expected {len(PIN_IDS)} images, got {len(images)}")
    update_config(images)
    print(f"Updated gallery config for {SLUG} with {len(images)} images.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
