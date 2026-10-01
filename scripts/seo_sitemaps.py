#!/usr/bin/env python3
import json, pathlib, subprocess
from xml.sax.saxutils import escape

ROOT=pathlib.Path(__file__).resolve().parents[1]
SITE="https://faramarzkowsari.github.io/"
BOOKS=ROOT/"books"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError):return d

def lastmod(path):
    try:
        out=subprocess.check_output(["git","log","-1","--format=%cs","--",str(path)],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        return out if out else None
    except Exception:return None

def url_xml(url,mod=None):
    x=["  <url>",f"    <loc>{escape(url)}</loc>"]
    if mod:x.append(f"    <lastmod>{escape(mod)}</lastmod>")
    x.append("  </url>")
    return "\n".join(x)

def write_map(path,rows):
    body='\n'.join(url_xml(u,m) for u,m in rows)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+body+'\n</urlset>\n',encoding="utf-8")

def write_sitemap_index(path,urls):
    body='\n'.join(
        "  <sitemap>\n    <loc>"+escape(url)+"</loc>\n  </sitemap>" for url in urls
    )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        +body+'\n</sitemapindex>\n',
        encoding="utf-8"
    )

projects=load(ROOT/"projects.json",[])
completed=load(BOOKS/"completed.json",{})
extra=load(BOOKS/"source-reviewed-extra.json",{})

# Include every real, published book landing page. completed/extra remain useful
# sources, but newly published catalog pages must never disappear from the sitemap
# just because their full PDF source review is still pending.
slugs=[]
for s in list(completed)+list(extra):
    if isinstance(s,str) and s.strip(): slugs.append(s.strip('/'))
for p in BOOKS.glob("*/index.html"):
    if p.parent.name and p.parent.name not in {".",".."}: slugs.append(p.parent.name)
slugs=list(dict.fromkeys(slugs))

book_rows=[(SITE+"books/",lastmod("books/index.html"))]
for slug in sorted(slugs):
    p=f"books/{slug}/index.html"
    if (ROOT/p).exists():book_rows.append((SITE+f"books/{slug}/",lastmod(p)))
write_map(BOOKS/"sitemap.xml",book_rows)

rows=[(SITE,lastmod("index.html"))]
for p in projects:
    if p.get("has_pages"):
        mod=(p.get("pushed_at") or "")[:10] or None
        rows.append((SITE+p.get("name","").strip('/')+"/",mod))
rows.extend(book_rows)
seen=set(); uniq=[]
for row in rows:
    if row[0] not in seen:seen.add(row[0]);uniq.append(row)
write_map(ROOT/"sitemap.xml",uniq)

# One stable sitemap index gives any standards-compliant search engine a single
# discovery URL while retaining the existing individual sitemap endpoints.
sitemap_urls=[
    SITE+"sitemap.xml",
    SITE+"books/sitemap.xml",
    SITE+"turkiye-disaster-intelligence-digital-twin/sitemap.xml",
]
write_sitemap_index(ROOT/"sitemap-index.xml",sitemap_urls)

print(f"SEO sitemaps: {len(book_rows)} book URLs; {len(uniq)} master URLs; {len(sitemap_urls)} maps in sitemap index.")
