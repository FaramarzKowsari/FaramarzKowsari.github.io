import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
DATA = BOOKS_DIR / "pinterest-infographics.json"
START = "<!-- pinterest-infographics:start -->"
END = "<!-- pinterest-infographics:end -->"
PINIT = '<script async defer src="https://assets.pinterest.com/js/pinit.js"></script>'


def esc(value):
    return html.escape(str(value or ""), quote=True)


def pin_id(pin_url):
    match = re.search(r"/pin/(\d+)/?", str(pin_url or ""))
    return match.group(1) if match else ""


def render_card(pin, google_url):
    title = esc(pin.get("title") or "Book infographic")
    desc = esc(pin.get("description") or "")
    alt = esc(pin.get("alt_text") or pin.get("title") or "Book infographic")
    pin_url = esc(pin.get("pin_url") or "")
    image_url = esc(pin.get("image_url") or "")

    if image_url:
        media = f'''<a class="pinterest-infographic-image-link" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer" aria-label="View or buy the book on Google Books">
          <img src="{image_url}" alt="{alt}" title="{title}" loading="lazy" decoding="async">
        </a>'''
    else:
        media = f'''<div class="pinterest-pin-embed" aria-label="{alt}">
          <a data-pin-do="embedPin" href="{pin_url}"></a>
        </div>'''

    pin_link = f'<a class="pinterest-source-link" href="{pin_url}" target="_blank" rel="noopener noreferrer">View this infographic on Pinterest</a>' if pin_url else ""

    return f'''    <figure class="pinterest-infographic-card">
      <h3>{title}</h3>
      {media}
      <figcaption>{desc}</figcaption>
      <div class="pinterest-infographic-actions">
        <a class="action primary" href="{esc(google_url)}" target="_blank" rel="noopener noreferrer">View / Buy on Google Books</a>
        {pin_link}
      </div>
    </figure>'''


def render_section(config):
    title = esc(config.get("section_title") or "Visual Guides & Infographics")
    intro = esc(config.get("intro") or "")
    google_url = config.get("google_books_url") or ""
    cards = "\n".join(render_card(pin, google_url) for pin in (config.get("pins") or []))
    return f'''{START}
<section class="section pinterest-infographics" aria-labelledby="pinterest-infographics-title">
  <style>
    .pinterest-infographics{{margin-top:44px;padding-top:30px}}
    .pinterest-infographics>p{{max-width:820px}}
    .pinterest-infographic-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;margin-top:24px}}
    .pinterest-infographic-card{{margin:0;padding:20px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.05)}}
    .pinterest-infographic-card h3{{margin:0 0 14px;font-size:20px;line-height:1.35}}
    .pinterest-infographic-image-link{{display:block;text-decoration:none}}
    .pinterest-infographic-image-link img{{display:block;width:100%;height:auto;aspect-ratio:2/3;object-fit:cover;border-radius:14px;border:1px solid var(--line);background:#f3f4f6}}
    .pinterest-pin-embed{{min-height:360px;display:flex;align-items:flex-start;justify-content:center;border-radius:14px;overflow:hidden;background:#f8fafc;padding:8px}}
    .pinterest-infographic-card figcaption{{margin-top:14px;font-size:15px;line-height:1.65;color:var(--muted)}}
    .pinterest-infographic-actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px}}
    .pinterest-infographic-actions .action{{margin:0}}
    .pinterest-source-link{{font-size:14px;font-weight:700;text-underline-offset:.16em}}
    @media(max-width:760px){{.pinterest-infographic-grid{{grid-template-columns:1fr}}}}
  </style>
  <h2 id="pinterest-infographics-title">{title}</h2>
  <p>{intro}</p>
  <div class="pinterest-infographic-grid">
{cards}
  </div>
</section>
{END}'''


def replace_or_insert(text, block):
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    if "</main>" in text:
        return text.replace("</main>", block + "\n</main>", 1)
    return text + "\n" + block + "\n"


def ensure_pinterest_script(text, needs_embed):
    if not needs_embed or "assets.pinterest.com/js/pinit.js" in text:
        return text
    if "</body>" in text:
        return text.replace("</body>", PINIT + "\n</body>", 1)
    return text + "\n" + PINIT + "\n"


def main():
    if not DATA.exists():
        print("No Pinterest infographic data file; nothing to do.")
        return

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("books/pinterest-infographics.json must contain a JSON object")

    updated = 0
    for slug, config in payload.items():
        page = BOOKS_DIR / slug / "index.html"
        if not page.exists():
            print(f"Skipping missing book page: {slug}")
            continue
        pins = config.get("pins") or []
        if not pins:
            continue
        text = page.read_text(encoding="utf-8")
        block = render_section(config)
        text = replace_or_insert(text, block)
        needs_embed = any(not pin.get("image_url") and pin_id(pin.get("pin_url")) for pin in pins)
        text = ensure_pinterest_script(text, needs_embed)
        page.write_text(text, encoding="utf-8")
        updated += 1

    print(f"Updated Pinterest infographic sections on {updated} book page(s).")


if __name__ == "__main__":
    main()
