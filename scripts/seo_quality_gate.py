#!/usr/bin/env python3
"""Fail the book build when durable SEO invariants are missing.

The gate checks technical completeness, not rankings. Search position can never be
guaranteed, but every public book page should expose a consistent, crawlable set
of signals: canonical URL, description, semantic Book data, breadcrumbs,
localized alternates, cover semantics, internal related links and topic-hub
membership.
"""

from __future__ import annotations
import html
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
BOOKS=ROOT/"books"
DATA=BOOKS/"books.json"
SEO_DATA=BOOKS/"seo-keywords.json"
BOOKS_BASE="https://faramarzkowsari.github.io/books"

SCRIPT_RE=re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',re.I|re.S)
META_RE=re.compile(r'<meta\b[^>]*>',re.I)
ATTR_RE=re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''',re.I|re.S)

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,OSError):return default

def clean(v):return re.sub(r"\s+"," ",str(v or "")).strip()

def meta_value(text,key,attr="name"):
    for m in META_RE.finditer(text):
        attrs={a.group(1).lower():html.unescape(a.group(3)) for a in ATTR_RE.finditer(m.group(0))}
        if attrs.get(attr,"").lower()==key.lower():return attrs.get("content","")
    return ""

def canonical(text):
    m=re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',text,re.I)
    return html.unescape(m.group(1)).strip() if m else ""

def json_types(text):
    found=[]
    for m in SCRIPT_RE.finditer(text):
        try:payload=json.loads(m.group(1).strip())
        except json.JSONDecodeError:continue
        stack=[payload]
        while stack:
            node=stack.pop()
            if isinstance(node,dict):
                t=node.get("@type")
                if isinstance(t,list):found.extend(str(x) for x in t)
                elif t:found.append(str(t))
                stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
            elif isinstance(node,list):stack.extend(node)
    return found

def book_nodes(text):
    out=[]
    for m in SCRIPT_RE.finditer(text):
        try:payload=json.loads(m.group(1).strip())
        except json.JSONDecodeError:continue
        stack=[payload]
        while stack:
            node=stack.pop()
            if isinstance(node,dict):
                t=node.get("@type")
                if t=="Book" or (isinstance(t,list) and "Book" in t):out.append(node)
                stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
            elif isinstance(node,list):stack.extend(node)
    return out

def has_cover_alt(text,cover):
    if not cover:return True
    for m in re.finditer(r'<img\b[^>]*>',text,re.I):
        tag=html.unescape(m.group(0))
        if "books.google.com/books/content" in tag or cover.split("&",1)[0] in tag:
            am=re.search(r'\balt=["\']([^"\']*)',tag,re.I)
            return bool(am and clean(am.group(1)))
    return False

books=load(DATA,[])
profiles=load(SEO_DATA,{})
errors=[];warnings=[];checked=0;localized_checked=0

if not isinstance(books,list):errors.append("books/books.json is not a JSON array")
if not isinstance(profiles,dict):errors.append("books/seo-keywords.json is not a JSON object")

for book in books if isinstance(books,list) else []:
    slug=clean(book.get("slug"))
    if not slug or book.get("status","active")!="active":continue
    path=BOOKS/slug/"index.html"
    if not path.exists():continue
    checked+=1
    profile=profiles.get(slug)
    if not isinstance(profile,dict):
        errors.append(f"{slug}: missing semantic SEO profile")
        continue
    if not clean(profile.get("primary_query")):errors.append(f"{slug}: missing primary query")
    if len(profile.get("secondary_queries") or [])<2:errors.append(f"{slug}: fewer than 2 secondary queries")
    if len(profile.get("long_tail_queries") or [])<2:errors.append(f"{slug}: fewer than 2 long-tail queries")
    if not profile.get("cluster"):errors.append(f"{slug}: missing topic cluster")
    if len(profile.get("related_slugs") or [])<1 and len(profiles)>1:warnings.append(f"{slug}: no semantic related books")

    gid=clean(book.get("google_books_id"))
    if gid:
        if not clean(book.get("google_books_url")):errors.append(f"{slug}: Google Books URL missing")
        if not clean(book.get("cover_url")):errors.append(f"{slug}: external Google Books cover missing")

    text=path.read_text(encoding="utf-8")
    expected=f"{BOOKS_BASE}/{slug}/"
    if canonical(text)!=expected:errors.append(f"{slug}: canonical mismatch ({canonical(text)!r})")
    desc=meta_value(text,"description")
    if not clean(desc):errors.append(f"{slug}: meta description missing")
    elif len(clean(desc))<55:warnings.append(f"{slug}: meta description is very short ({len(clean(desc))})")
    if re.search(r'<meta\b[^>]*name=["\']keywords["\']',text,re.I):errors.append(f"{slug}: obsolete meta keywords tag remains")
    if "<!-- semantic-seo:start -->" not in text:errors.append(f"{slug}: semantic SEO head block missing")
    types=json_types(text)
    if "Book" not in types:errors.append(f"{slug}: Book JSON-LD missing")
    if "BreadcrumbList" not in types:errors.append(f"{slug}: BreadcrumbList JSON-LD missing")
    nodes=book_nodes(text)
    if nodes:
        node=nodes[0]
        if not node.get("keywords"):errors.append(f"{slug}: Book schema keywords missing")
        if not node.get("about"):errors.append(f"{slug}: Book schema about entities missing")
    if clean(book.get("cover_url")) and not has_cover_alt(text,clean(book.get("cover_url"))):
        errors.append(f"{slug}: cover image ALT missing")
    if 'hreflang="x-default"' not in text:errors.append(f"{slug}: x-default hreflang missing")
    if profile.get("related_slugs") and "<!-- semantic-related-books:start -->" not in text:
        errors.append(f"{slug}: semantic related-books block missing")

    for loc in ("ru","tr","de","es","fr","pt-br"):
        lp=BOOKS/slug/loc/"index.html"
        if not lp.exists():continue
        localized_checked+=1
        lt=lp.read_text(encoding="utf-8")
        if not clean(meta_value(lt,"description")):errors.append(f"{slug}/{loc}: meta description missing")
        if re.search(r'<meta\b[^>]*name=["\']keywords["\']',lt,re.I):errors.append(f"{slug}/{loc}: obsolete meta keywords tag remains")
        ltypes=json_types(lt)
        if "Book" not in ltypes:errors.append(f"{slug}/{loc}: nested Book schema missing")
        if "BreadcrumbList" not in ltypes:errors.append(f"{slug}/{loc}: BreadcrumbList missing")
        lnodes=book_nodes(lt)
        if lnodes and not lnodes[0].get("keywords"):errors.append(f"{slug}/{loc}: localized schema keywords missing")
        if profile.get("related_slugs") and "<!-- semantic-related-books:start -->" not in lt:
            errors.append(f"{slug}/{loc}: localized related-books block missing")

if not (BOOKS/"topics"/"index.html").exists():errors.append("topics index missing")
elif "<!-- semantic-topic-hubs:start -->" not in (BOOKS/"topics"/"index.html").read_text(encoding="utf-8"):
    errors.append("topics index is not linked to semantic topic hubs")
if not (BOOKS/"sitemap-topics.xml").exists():errors.append("books/sitemap-topics.xml missing")

print(f"SEO quality gate checked {checked} base book pages and {localized_checked} localized book pages.")
for item in warnings[:50]:print("WARNING:",item)
if len(warnings)>50:print(f"WARNING: {len(warnings)-50} additional warning(s) omitted.")

if errors:
    for item in errors[:100]:print("ERROR:",item)
    if len(errors)>100:print(f"ERROR: {len(errors)-100} additional error(s) omitted.")
    print(f"SEO quality gate FAILED with {len(errors)} error(s).")
    sys.exit(1)

print(f"SEO quality gate PASSED with {len(warnings)} warning(s).")
