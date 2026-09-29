#!/usr/bin/env python3
"""Merge source-grounded Library enrichment into books/completed.json.

The enrichment file contains public-facing descriptions derived from the user's
Library source books. It is intentionally separate from the generated catalog so
source-backed rich metadata survives subsequent page rebuilds.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
COMPLETED = BOOKS / "completed.json"
ENRICHED = BOOKS / "library-source-enriched.json"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def main():
    completed = load(COMPLETED, {})
    enriched = load(ENRICHED, {})

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
    print(f"Applied Library source enrichment to {changed} book record(s).")


if __name__ == "__main__":
    main()
