"""Add the site's GA4 collection script to new or regenerated catalog pages."""
from pathlib import Path

BOOKS = Path(__file__).resolve().parents[1] / "books"
TAG = b'<script defer src="/books/analytics.js"></script>'

if __name__ == "__main__":
    updated = 0
    for page in BOOKS.rglob("*.html"):
        data = page.read_bytes()
        if TAG in data:
            continue
        offset = data.lower().find(b"</head>")
        if offset < 0:
            raise ValueError(f"Missing head in {page}")
        page.write_bytes(data[:offset] + TAG + b"\n" + data[offset:])
        updated += 1
    print(f"Added book analytics to {updated} pages.")
