#!/usr/bin/env python3
import html, json, pathlib, re, subprocess
from xml.sax.saxutils import escape

ROOT=pathlib.Path(__file__).resolve().parents[1]
SITE="https://faramarzkowsari.github.io/"
BOOKS=ROOT/"books"
LOCALIZED_SITEMAPS=("ru","tr","de","es","fr","pt-br")

META_TAG_RE=re.compile(r"<meta\b[^>]*>",re.I)
ATTR_RE=re.compile(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''',re.I|re.S)
SCRIPT_RE=re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I|re.S,
)
CANONICAL_RE=re.compile(
    r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',
    re.I,
)

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

def meta_value(text,key,attr_name):
    key_l=key.lower()
    for match in META_TAG_RE.finditer(text):
        data={m.group(1).lower():html.unescape(m.group(3)) for m in ATTR_RE.finditer(match.group(0))}
        if data.get(attr_name,"").lower()==key_l:
            return data.get("content")
    return None

def canonical_value(text):
    match=CANONICAL_RE.search(text)
    return html.unescape(match.group(1)) if match else None

def json_has_type(node,wanted):
    if isinstance(node,dict):
        node_type=node.get("@type")
        if node_type==wanted or (isinstance(node_type,list) and wanted in node_type):
            return True
        return any(json_has_type(v,wanted) for v in node.values() if isinstance(v,(dict,list)))
    if isinstance(node,list):
        return any(json_has_type(v,wanted) for v in node if isinstance(v,(dict,list)))
    return False

def has_book_schema(text):
    for match in SCRIPT_RE.finditer(text):
        try:data=json.loads(match.group(1).strip())
        except json.JSONDecodeError:continue
        if json_has_type(data,"Book"):
            return True
    return False

def is_book_landing(text):
    return (meta_value(text,"og:type","property") or "").lower()=="book" or has_book_schema(text)

def image_sitemap_rows():
    rows={}
    for path in BOOKS.rglob("index.html"):
        try:text=path.read_text(encoding="utf-8")
        except OSError:continue
        # Include base pages and every localized landing page that carries a
        # Book entity, even when its Open Graph type is intentionally website.
        if not is_book_landing(text):
            continue
        page=canonical_value(text)
        image=meta_value(text,"og:image","property") or meta_value(text,"twitter:image","name")
        if not page or not image or not re.match(r"^https?://",image,re.I):
            continue
        rows[page]=image
    return sorted(rows.items())

def write_image_map(path,rows):
    parts=[
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
    ]
    for page,image in rows:
        parts.extend([
            "  <url>",
            f"    <loc>{escape(page)}</loc>",
            "    <image:image>",
            f"      <image:loc>{escape(image)}</image:loc>",
            "    </image:image>",
            "  </url>",
        ])
    parts.append("</urlset>")
    path.write_text("\n".join(parts)+"\n",encoding="utf-8")

projects=load(ROOT/"projects.json",[])
completed=load(BOOKS/"completed.json",{})
extra=load(BOOKS/"source-reviewed-extra.json",{})

# Include every real, published base-language book landing page. Localized
# page discovery remains in the per-language sitemaps and image sitemap.
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

# Image sitemap: page HTML stays on GitHub Pages while every cover remains on
# its original external host. No cover bytes are downloaded, proxied or stored.
image_rows=image_sitemap_rows()
write_image_map(BOOKS/"image-sitemap.xml",image_rows)

# One stable sitemap index gives standards-compliant engines a single discovery
# URL while retaining the existing individual sitemap endpoints.
sitemap_urls=[
    SITE+"sitemap.xml",
    SITE+"books/sitemap.xml",
    SITE+"books/image-sitemap.xml",
]
for locale in LOCALIZED_SITEMAPS:
    filename=f"sitemap-{locale}.xml"
    if (BOOKS/filename).exists():
        sitemap_urls.append(SITE+"books/"+filename)
sitemap_urls.append(SITE+"turkiye-disaster-intelligence-digital-twin/sitemap.xml")
write_sitemap_index(ROOT/"sitemap-index.xml",sitemap_urls)

print(f"SEO sitemaps: {len(book_rows)} book URLs; {len(image_rows)} image-page pairs across all languages; {len(uniq)} master URLs; {len(sitemap_urls)} maps in sitemap index.")
