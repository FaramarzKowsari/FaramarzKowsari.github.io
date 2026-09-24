import json, pathlib, html, re, unicodedata
# This generator is intentionally simple. The source of truth is books/books.json.
# It can be extended later to regenerate all book pages after metadata/PDF enrichment.
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "books" / "books.json"
books = json.loads(DATA.read_text(encoding="utf-8"))
print(f"Loaded {len(books)} book records from {DATA}")
print("Static book pages are already generated in this v1 package.")
