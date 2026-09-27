#!/usr/bin/env python3
import html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
B = ROOT / "books"
DATA, COMPLETED, EXTRA = B/"books.json", B/"completed.json", B/"source-reviewed-extra.json"
BASE = "https://faramarzkowsari.github.io/books"
AUTHOR = "Faramarz Kowsari"
LANG = {"English":"en","Türkçe":"tr","Turkish":"tr","Español":"es","Spanish":"es","Français":"fr","French":"fr","Deutsch":"de","German":"de","فارسی":"fa","Persian":"fa"}
LOCALE = {"en":"en_US","tr":"tr_TR","es":"es_ES","fr":"fr_FR","de":"de_DE","fa":"fa_IR"}

def load(p, d):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError: return d

def esc(x): return html.escape(str(x or ""), quote=True)
def code(b): return b.get("language_code") or LANG.get(b.get("language"), "en")

books, completed, extra = load(DATA, []), load(COMPLETED, {}), load(EXTRA, {})
by_slug = {b.get("slug"): b for b in books if b.get("slug")}
ready = set(completed) | set(extra)
for slug in ready:
    b = by_slug.get(slug)
    if not b: continue
    for src in (completed.get(slug, {}), extra.get(slug, {})):
        for k,v in src.items():
            if v not in ("", None, [], {}): b[k] = v
    b["status"], b["content_status"] = "active", "complete"
DATA.write_text(json.dumps(books, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

groups = {}
for b in books:
    g=b.get("translation_group")
    if g and b.get("slug") in ready: groups.setdefault(g, []).append(b)

def alternates(b):
    rows=groups.get(b.get("translation_group"), [])
    if len(rows)<2: return "", ""
    seen=set(); links=[]; locales=[]
    for x in sorted(rows, key=lambda z:(code(z)!="en", code(z), z.get("sequence") or 0)):
        c=code(x)
        if c in seen: continue
        seen.add(c)
        links.append(f'<link rel="alternate" hreflang="{esc(c)}" href="{BASE}/{esc(x["slug"])}/">')
        if x.get("slug")!=b.get("slug"): locales.append(f'<meta property="og:locale:alternate" content="{esc(LOCALE.get(c,c))}">')
    default=next((x for x in rows if code(x)=="en"), rows[0])
    links.append(f'<link rel="alternate" hreflang="x-default" href="{BASE}/{esc(default["slug"])}/">')
    return "\n".join(links), "\n".join(locales)

def enhance_page(b):
    p=B/b["slug"]/"index.html"
    if not p.exists(): return False
    s=p.read_text(encoding="utf-8"); old=s
    c=code(b); title=b.get("title") or "Book"; cover=b.get("cover_url") or ""
    s=re.sub(r'<meta name="robots"[^>]*>', '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">', s, count=1)
    additions=[]
    if 'name="author"' not in s: additions.append(f'<meta name="author" content="{AUTHOR}">')
    if 'rel="sitemap"' not in s: additions.append('<link rel="sitemap" type="application/xml" href="../sitemap.xml">')
    if 'property="og:site_name"' not in s: additions.append('<meta property="og:site_name" content="Faramarz Kowsari Books">')
    if 'property="og:locale"' not in s: additions.append(f'<meta property="og:locale" content="{LOCALE.get(c,"en_US")}">')
    alts, altlocales=alternates(b)
    if alts and 'hreflang=' not in s: additions.append(alts)
    if altlocales and 'og:locale:alternate' not in s: additions.append(altlocales)
    if 'name="twitter:title"' not in s: additions.append(f'<meta name="twitter:title" content="{esc(title)}">')
    if cover and 'name="twitter:image"' not in s: additions.append(f'<meta name="twitter:image" content="{esc(cover)}">')
    if cover and 'property="og:image:alt"' not in s: additions.append(f'<meta property="og:image:alt" content="Cover of {esc(title)} by {AUTHOR}">')
    if additions:
        marker='<link rel="stylesheet"'; i=s.find(marker)
        if i>=0: s=s[:i]+"\n".join(additions)+"\n"+s[i:]
        else: s=s.replace('</head>', "\n".join(additions)+'\n</head>', 1)
    if 'class="breadcrumbs"' not in s:
        crumb=f'<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../">Home</a><span>›</span><a href="../">Books</a><span>›</span><span aria-current="page">{esc(title)}</span></nav>\n'
        s=s.replace('<main class="book-page">', '<main class="book-page">\n'+crumb, 1)
    if s!=old:
        p.write_text(s, encoding="utf-8"); return True
    return False

changed=sum(enhance_page(b) for b in books if b.get("slug") in ready and b.get("status")=="active")
ready_books=[b for b in books if b.get("slug") in ready and b.get("status")=="active"]
ready_books.sort(key=lambda b:(b.get("sequence") or 999999,(b.get("title") or "").lower()))
cards=[]; items=[]
for n,b in enumerate(ready_books,1):
    t=b.get("title") or "Untitled"; lang=b.get("language") or ""; cat=b.get("category") or ""; cov=b.get("cover_url") or ""; slug=b["slug"]
    detail=" · ".join(x for x in (lang,cat) if x) or "Source-reviewed book"
    cards.append(f'''<article class="card" data-search="{esc((t+' '+lang+' '+cat).lower())}"><a href="./{esc(slug)}/"><img class="cover" src="{esc(cov)}" alt="{esc(t)} book cover" loading="lazy" decoding="async"></a><div class="card-body"><h2><a href="./{esc(slug)}/">{esc(t)}</a></h2><div class="meta">{esc(detail)}</div><a class="btn" href="./{esc(slug)}/">View book</a></div></article>''')
    items.append({"@type":"ListItem","position":n,"url":f"{BASE}/{slug}/","name":t})
schema={"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":f"{BASE}/#collection","name":f"Books by {AUTHOR}","url":f"{BASE}/","description":"Multilingual source-reviewed books by Faramarz Kowsari with direct Google Books links.","author":{"@id":"https://faramarzkowsari.github.io/#person"},"mainEntity":{"@id":f"{BASE}/#book-list"}},{"@type":"ItemList","@id":f"{BASE}/#book-list","numberOfItems":len(items),"itemListElement":items},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://faramarzkowsari.github.io/"},{"@type":"ListItem","position":2,"name":"Books","item":f"{BASE}/"}]}]}
index=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="p:domain_verify" content="3c53b20efafb307ca27f2bcf223188ea"><meta name="author" content="{AUTHOR}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><title>Books by Faramarz Kowsari | AI, Trading, Business & Personal Growth</title><meta name="description" content="Browse source-reviewed books by Faramarz Kowsari across artificial intelligence, trading, business, technology, personal growth and multilingual editions, with direct Google Books links."><link rel="canonical" href="{BASE}/"><link rel="sitemap" type="application/xml" href="./sitemap.xml"><meta property="og:type" content="website"><meta property="og:site_name" content="Faramarz Kowsari Books"><meta property="og:title" content="Books by Faramarz Kowsari"><meta property="og:description" content="A multilingual library of source-reviewed book pages with direct Google Books links."><meta property="og:url" content="{BASE}/"><meta property="og:image" content="https://github.com/FaramarzKowsari.png"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Books by Faramarz Kowsari"><meta name="twitter:description" content="AI, trading, business, technology and personal-growth books with permanent source-reviewed pages."><meta name="twitter:image" content="https://github.com/FaramarzKowsari.png"><link rel="stylesheet" href="./styles.css"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script></head><body><main class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Home</a><span>›</span><span aria-current="page">Books</span></nav><header class="hero"><h1>Books by Faramarz Kowsari</h1><p>A growing multilingual library spanning artificial intelligence, trading, business, technology, personal growth and related subjects. Every source-reviewed title below has a permanent crawlable page and a direct Google Books destination.</p><div class="actions"><a class="action primary" href="https://play.google.com/store/search?q=Faramarz%20Kowsari&c=books" target="_blank" rel="noopener noreferrer">Find Faramarz Kowsari on Google Books</a><a class="action" href="../">Author home</a></div></header><section><h2>Source-reviewed book pages</h2><p id="completed-count" class="count">{len(ready_books)} crawlable book pages.</p><div class="toolbar"><input id="q" type="search" placeholder="Search by title, language or category..." aria-label="Search books"></div><div id="completed-grid" class="grid">{''.join(cards)}</div></section></main><script>(function(){{const q=document.getElementById('q'),cs=[...document.querySelectorAll('.card')],c=document.getElementById('completed-count');q.addEventListener('input',()=>{{let n=0,t=q.value.trim().toLowerCase();cs.forEach(x=>{{let v=!t||x.dataset.search.includes(t);x.hidden=!v;if(v)n++}});c.textContent=n+' crawlable book page'+(n===1?'':'s')+'.'}})}})();</script></body></html>'''
(B/"index.html").write_text(index, encoding="utf-8")
print(f"SEO: {len(ready_books)} reviewed books; {changed} page heads enhanced; static books index generated.")