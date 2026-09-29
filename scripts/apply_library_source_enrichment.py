#!/usr/bin/env python3
"""Merge source-grounded Library enrichment into books/completed.json.

Public-facing enrichment is kept in one or more
books/library-source-enriched*.json files. Splitting the curated metadata lets us
expand coverage without turning generated catalog metadata into a hand-edited file.
Later enrichment files may refine earlier fields for the same slug.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
COMPLETED = BOOKS / "completed.json"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def main():
    completed = load(COMPLETED, {})
    enrichment_paths = sorted(BOOKS.glob("library-source-enriched*.json"))
    enriched = {}
    for path in enrichment_paths:
        payload = load(path, {})
        if not isinstance(payload, dict):
            raise SystemExit(f"Expected an object in {path}")
        for slug, metadata in payload.items():
            if not isinstance(metadata, dict):
                continue
            enriched.setdefault(slug, {}).update(metadata)

    changed = 0
    for slug, metadata in enriched.items():
        current = dict(completed.get(slug, {}))
        merged = dict(current)
        for key, value in metadata.items():
            if value not in ("", None, [], {}):
                merged[key] = value
        if merged != current:
            completed[slug] = merged
            changed += 1

    COMPLETED.write_text(
        json.dumps(completed, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Applied Library source enrichment from {len(enrichment_paths)} file(s) "
        f"to {changed} book record(s)."
    )


if __name__ == "__main__":
    main()
