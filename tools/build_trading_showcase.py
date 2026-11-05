#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
SHOWCASE = ROOT / "trading-books"
TEMPLATE = SHOWCASE / "template.html"
DATA = SHOWCASE / "data" / "trading-books.json"
INDEX = SHOWCASE / "index.html"

CATEGORY_ORDER = [
    "Start Here & Core Technical Analysis",
    "Smart Money, Liquidity & Market Structure",
    "Order Flow, Volume & Market Microstructure",
    "Futures & Index Trading",
    "Options & Volatility",
    "Scalping & Day Trading",
    "Swing, Trend & Indicator Trading",
    "Gold, Silver, Forex & Crypto",
    "AI, Algorithmic & Systematic Trading",
    "Trading Risk, Execution & Professional Practice",
]

CATEGORY_BLURBS = {
    "Start Here & Core Technical Analysis": "Foundational books for reading price, structure, levels, breakouts, confluence and chart behavior with a practical trading lens.",
    "Smart Money, Liquidity & Market Structure": "Liquidity, institutional-style structure, Fair Value Gaps, order blocks, CHoCH/BOS, ICT concepts and related execution frameworks.",
    "Order Flow, Volume & Market Microstructure": "Books for traders who want to read the auction more closely through footprint, DOM, Level 2, delta, CVD, VWAP, volume and liquidity behavior.",
    "Futures & Index Trading": "Contract mechanics, Micro E-minis, index futures, margin, execution, sessions, risk and professional futures workflows.",
    "Options & Volatility": "Same-day options, gamma, options flow, volatility, Greeks, structures and fast-moving derivatives decision-making.",
    "Scalping & Day Trading": "Fast intraday frameworks for session structure, opening behavior, short-horizon execution, scalping and disciplined day-trading decisions.",
    "Swing, Trend & Indicator Trading": "Trend and swing frameworks using Ichimoku, MACD, Renko, Heikin Ashi, moving averages and multi-timeframe confirmation without indicator worship.",
    "Gold, Silver, Forex & Crypto": "Market-specific books for XAUUSD, silver, currencies and crypto, with attention to volatility, sessions, liquidity and execution constraints.",
    "AI, Algorithmic & Systematic Trading": "AI-assisted, algorithmic and reproducible trading workflows that turn ideas into rules, tests, data pipelines and controlled decision systems.",
    "Trading Risk, Execution & Professional Practice": "Risk, funded accounts, institutional-vs-retail realities, process design, execution discipline and professional trading practice.",
}

CATEGORY_PAGE_SLUGS = {
    "Start Here & Core Technical Analysis": "technical-analysis-books",
    "Smart Money, Liquidity & Market Structure": "smart-money-trading-books",
    "Order Flow, Volume & Market Microstructure": "order-flow-trading-books",
    "Futures & Index Trading": "futures-trading-books",
    "Options & Volatility": "options-trading-books",
    "Scalping & Day Trading": "scalping-day-trading-books",
    "Swing, Trend & Indicator Trading": "swing-trading-books",
    "Gold, Silver, Forex & Crypto": "gold-forex-crypto-trading-books",
    "AI, Algorithmic & Systematic Trading": "algorithmic-ai-trading-books",
    "Trading Risk, Execution & Professional Practice": "trading-risk-execution-books",
}

CATEGORY_SEARCH_TITLES = {
    "Start Here & Core Technical Analysis": "Technical Analysis & Price Action Trading Books",
    "Smart Money, Liquidity & Market Structure": "Smart Money Concepts & Liquidity Trading Books",
    "Order Flow, Volume & Market Microstructure": "Order Flow Trading Books: Footprint, DOM, CVD & Volume",
    "Futures & Index Trading": "Futures Trading Books: Micro E-mini, Index Futures & Execution",
    "Options & Volatility": "Options Trading Books: 0DTE, Gamma, Flow & Volatility",
    "Scalping & Day Trading": "Scalping & Day Trading Books",
    "Swing, Trend & Indicator Trading": "Swing Trading & Trend Analysis Books",
    "Gold, Silver, Forex & Crypto": "Gold, Forex, Silver & Crypto Trading Books",
    "AI, Algorithmic & Systematic Trading": "Algorithmic, AI & Systematic Trading Books",
    "Trading Risk, Execution & Professional Practice": "Trading Risk, Execution & Prop Firm Books",
}

CATEGORY_LONG_INTROS = {
    "Start Here & Core Technical Analysis": "Technical analysis becomes useful when it gives a trader a repeatable language for describing what price has already done and what would invalidate a current idea. This collection focuses on price action, candlesticks, support and resistance, breakouts, Wyckoff structure, Fibonacci, confluence and related chart-reading skills. It is designed for readers who want a stronger foundation before moving into specialized tools such as order flow, options or algorithmic systems. The emphasis is on reading structure clearly, separating observation from prediction, and connecting every setup to risk and invalidation.",
    "Smart Money, Liquidity & Market Structure": "This collection focuses on the vocabulary and decision frameworks commonly grouped under Smart Money Concepts: market structure, liquidity, displacement, Fair Value Gaps, order blocks, CHoCH, BOS, premium and discount, inducement, breaker blocks and ICT-style timing ideas. The books are organized around a simple requirement: a concept should be defined clearly enough to recognize, reject and test. That matters because liquidity-based chart language can become retrospective if every move is explained only after the fact. These titles emphasize context, invalidation and evidence rather than treating institutional-sounding terminology as a guarantee.",
    "Order Flow, Volume & Market Microstructure": "Order-flow trading asks what happened inside and around the candle rather than relying only on the finished bar. This collection covers footprint charts, cumulative volume delta, DOM, Level 2 market data, volume profile, VWAP, liquidation heatmaps and related microstructure tools. Each view answers a different question: traded volume, aggressive flow, displayed liquidity, value by price, or the relationship between price and volume-weighted reference levels. The purpose of this collection is to help traders choose the correct layer of market information for the decision they are actually making.",
    "Futures & Index Trading": "Futures trading combines chart analysis with contract mechanics that directly affect risk and execution. These books cover Micro E-mini and index futures, contract specifications, tick value, margin, session structure, order flow, VWAP, volume profile, slippage, backtesting and professional execution. They are intended for traders who want to understand not only where a setup appears on the chart, but also what instrument is being traded, how the contract behaves, and how sizing and execution translate an idea into real account exposure.",
    "Options & Volatility": "Options introduce dimensions that do not exist in a simple directional trade: expiration, strike selection, implied volatility, liquidity and the Greeks. This collection ranges from calls, puts and option chains to 0DTE trading, gamma exposure and options flow. It is built for readers who want to understand why being correct about direction is not always enough, how time and volatility reshape a position, and how dealer positioning or unusual activity should be interpreted within the mechanics of the option itself.",
    "Scalping & Day Trading": "Short-horizon trading compresses the time available for analysis while making execution costs and discipline more important. This collection covers scalping, day trading, opening ranges, first-hour structure, failed breakouts and intraday trade management. The books emphasize session context, precise invalidation, realistic spreads and slippage, and the ability to stand aside when conditions do not justify a trade. The goal is not more activity; it is clearer decisions under faster conditions.",
    "Swing, Trend & Indicator Trading": "Swing and trend trading require a different relationship with time. These books cover Ichimoku, MACD, Renko, Heikin Ashi, moving averages, multi-timeframe analysis and broader swing-trading frameworks. Indicators are treated as transformations of price and market state rather than prediction machines. The collection is designed for readers who want to combine trend context, confirmation, entries, exits and risk without stacking indicators until every chart appears to agree.",
    "Gold, Silver, Forex & Crypto": "Different markets impose different execution environments. Gold and silver can react sharply to macroeconomic information and liquidity windows; forex is shaped by currency sessions and pair structure; crypto trades continuously and carries its own leverage and liquidation dynamics. This collection focuses on market-specific behavior in XAUUSD, XAGUSD and crypto-related trading, while keeping risk, liquidity, volatility and instrument mechanics at the center of the decision.",
    "AI, Algorithmic & Systematic Trading": "Systematic and AI-assisted trading moves discretion into rules, data definitions, models, testing assumptions and production controls. These books cover AI trading agents, trading bots, chatbot-assisted workflows, multi-timeframe evidence, strategy specification and controlled automation. The central standard is reproducibility: an idea should be clear enough to test, costs should be included, leakage and overfitting should be challenged, and automation should never bypass independent risk controls.",
    "Trading Risk, Execution & Professional Practice": "Trading performance is constrained by survival. This collection focuses on drawdown, funded-account rules, execution, institutional-versus-retail differences, leverage and the operational realities that sit around a strategy. It is for traders who want to understand why a valid market idea can still fail when sizing, liquidity, account constraints or execution are ignored. The books emphasize process, failure boundaries and the practical architecture of risk.",
}

TRADING_PHRASES = [
    "trading", "trader", "futures", "options", "forex", "xauusd", "xagusd",
    "ichimoku", "candlestick", "order flow", "footprint", "market structure",
    "smart money", "fair value gap", "order block", "liquidity sweep", "scalping",
    "swing trading", "day trading", "technical analysis", "vwap", "volume profile",
    "wyckoff", "renko", "heikin ashi", "macd", "fibonacci", "support & resistance",
    "support and resistance", "prop firm", "0dte", "gamma exposure", "dom trading",
    "level 2", "cumulative volume delta", "cvd", "micro e-mini", "e-mini",
    "price action", "breakout", "market microstructure", "volatility trading",
    "multiple timeframe", "multi-timeframe", "fibonacci", "wyckoff", "candlestick",
]

def clean_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def jsonld_blocks(source: str):
    for match in re.finditer(r'<script\s+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', source, flags=re.I):
        raw = match.group(1).strip()
        try:
            yield json.loads(raw)
        except json.JSONDecodeError:
            continue

def find_book_schema(source: str):
    for block in jsonld_blocks(source):
        nodes = block.get("@graph", []) if isinstance(block, dict) and "@graph" in block else [block]
        for node in nodes:
            if isinstance(node, dict):
                kind = node.get("@type")
                if kind == "Book" or (isinstance(kind, list) and "Book" in kind):
                    return node
    return None

def meta(source: str, key: str, prop=False) -> str:
    attr = "property" if prop else "name"
    pattern = rf'<meta\s+[^>]*{attr}=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']*)["\'][^>]*>'
    m = re.search(pattern, source, flags=re.I)
    if m:
        return html.unescape(m.group(1)).strip()
    pattern = rf'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*{attr}=["\']{re.escape(key)}["\'][^>]*>'
    m = re.search(pattern, source, flags=re.I)
    return html.unescape(m.group(1)).strip() if m else ""

def first_about_paragraph(source: str) -> str:
    m = re.search(r'<h2[^>]*>\s*About this book\s*</h2>([\s\S]*?)</section>', source, flags=re.I)
    if not m:
        return ""
    p = re.search(r'<p[^>]*>([\s\S]*?)</p>', m.group(1), flags=re.I)
    return clean_text(p.group(1)) if p else ""

def extract_google_id(schema: dict, source: str) -> str:
    ident = schema.get("identifier", [])
    if isinstance(ident, dict):
        ident = [ident]
    for item in ident:
        if isinstance(item, dict) and str(item.get("propertyID", "")).lower() == "google books id":
            return str(item.get("value", "")).strip()
    candidates = [str(schema.get("sameAs", "")), meta(source, "og:image", prop=True), source]
    for candidate in candidates:
        m = re.search(r'(?:[?&]id=|books/content\?id=)([A-Za-z0-9_-]+)', candidate)
        if m:
            return m.group(1)
    return ""

def extract_medium(schema: dict, source: str) -> str:
    subject = schema.get("subjectOf")
    if isinstance(subject, dict):
        url = str(subject.get("url", ""))
        if "medium.com/" in url:
            return url
    if isinstance(subject, list):
        for item in subject:
            if isinstance(item, dict) and "medium.com/" in str(item.get("url", "")):
                return str(item["url"])
    m = re.search(r'href=["\'](https://medium\.com/[^"\']+)["\']', source, flags=re.I)
    return html.unescape(m.group(1)) if m else ""

def about_names(schema: dict):
    values = schema.get("about", [])
    if isinstance(values, dict):
        values = [values]
    out = []
    for item in values:
        if isinstance(item, dict) and item.get("name"):
            out.append(clean_text(str(item["name"])))
        elif isinstance(item, str):
            out.append(clean_text(item))
    return out

def is_trading_book(book: dict) -> bool:
    genre = book["genre"].lower()
    title = book["title"].lower()
    blob = book["search_blob"].lower()
    if "trading" in genre or "financial markets" in genre or "algorithmic trading" in genre:
        return True
    if any(x in title for x in ["trading", "futures", "options", "forex", "xauusd", "xagusd", "ichimoku", "multiple timeframe", "multi-timeframe"]):
        return True
    score = sum(1 for phrase in TRADING_PHRASES if phrase in blob)
    return score >= 2

def category_for(book: dict) -> str:
    title = book["title"].lower()
    t = book["search_blob"].lower()

    # Title-first classification keeps the book's primary promise ahead of
    # secondary keywords that naturally appear in broad trading descriptions.
    if any(x in title for x in ["ai trading", "ai-assisted", "trading bot", "trading agent", "chatbot"]):
        return "AI, Algorithmic & Systematic Trading"
    if any(x in title for x in ["xauusd", "xagusd", "silver trading", "forex", "crypto trading"]):
        return "Gold, Silver, Forex & Crypto"
    if any(x in title for x in ["0dte", "options", "gamma exposure", "options flow"]):
        return "Options & Volatility"
    if any(x in title for x in ["futures", "micro e-mini", "e-mini", "e-nano"]):
        return "Futures & Index Trading"
    if any(x in title for x in ["footprint", "dom trading", "level 2", "cvd trading", "volume profile", "volume bubbles", "vwap", "liquidation heatmap"]):
        return "Order Flow, Volume & Market Microstructure"
    if any(x in title for x in ["smart money", "fair value gap", "order block", "liquidity sweep", "breaker block", "inducement", "premium & discount", "premium and discount", "ict ", "choch", "bos", "balanced price range", "market structure shift", "market structure trading", "supply and demand", "algorithmic time & price"]):
        return "Smart Money, Liquidity & Market Structure"
    if any(x in title for x in ["scalping", "day trading", "opening range", "first hour dealing range", "turtle soup"]):
        return "Scalping & Day Trading"
    if any(x in title for x in ["swing trading", "ichimoku", "renko", "heikin ashi", "macd", "moving average", "multi-timeframe", "multiple timeframe"]):
        return "Swing, Trend & Indicator Trading"
    if any(x in title for x in ["candlestick", "confluence trading", "fibonacci", "support & resistance", "support and resistance", "wyckoff", "false breakout", "beyond the single candle", "breakout & retest", "breakout and retest"]):
        return "Start Here & Core Technical Analysis"
    if any(x in title for x in ["prop firm", "funded account", "hedge fund"]):
        return "Trading Risk, Execution & Professional Practice"

    # Fallbacks for future titles whose names are less explicit.
    if any(x in t for x in ["ai trading", "algorithmic trading", "trading bot", "trading agent", "chatbot"]):
        return "AI, Algorithmic & Systematic Trading"
    if any(x in t for x in ["0dte", "options", "gamma exposure", "options flow", "volatility"]) and "futures" not in title:
        return "Options & Volatility"
    if any(x in t for x in ["footprint", "order flow", "market microstructure", "level 2", "dom trading", "cumulative volume delta", "cvd", "volume profile", "volume bubbles", "vwap"]):
        return "Order Flow, Volume & Market Microstructure"
    if any(x in t for x in ["smart money", "fair value gap", "order block", "liquidity sweep", "breaker block", "inducement", "premium & discount", "premium and discount", "ict ", "choch", "bos", "balanced price range", "market structure shift"]):
        return "Smart Money, Liquidity & Market Structure"
    if any(x in t for x in ["futures", "micro e-mini", "e-mini", "e-nano"]):
        return "Futures & Index Trading"
    if any(x in t for x in ["xauusd", "xagusd", "silver trading", "forex", "crypto"]):
        return "Gold, Silver, Forex & Crypto"
    if any(x in t for x in ["scalping", "day trading", "opening range", "first hour dealing range"]):
        return "Scalping & Day Trading"
    if any(x in t for x in ["swing trading", "ichimoku", "renko", "heikin ashi", "macd", "moving average", "trend trading", "multi-timeframe", "multiple timeframe"]):
        return "Swing, Trend & Indicator Trading"
    if any(x in t for x in ["prop firm", "funded account", "hedge fund", "risk management", "professional execution"]):
        return "Trading Risk, Execution & Professional Practice"
    return "Start Here & Core Technical Analysis"

def promotional_fallback(title: str, category: str) -> str:
    if "multiple timeframe" in title.lower() or "multi-timeframe" in title.lower():
        return "A focused trading guide to multiple timeframe analysis for readers who want to connect higher-timeframe market context with lower-timeframe structure and execution. It belongs in the trader’s toolkit for reducing tunnel vision, comparing trend and structure across chart horizons, and making more coherent decisions instead of treating each timeframe as an isolated market."
    by_category = {
        "Futures & Index Trading": "A practical futures trading title focused on turning contract knowledge, market structure, execution and risk into a clearer decision process for active traders.",
        "Options & Volatility": "A practical options and volatility trading title designed to help traders connect market mechanics, structure, execution and risk rather than relying on isolated signals.",
        "Order Flow, Volume & Market Microstructure": "A market-microstructure trading title for readers who want to read volume, liquidity and execution behavior with greater precision and less guesswork.",
        "Smart Money, Liquidity & Market Structure": "A focused trading guide to liquidity and market structure, built for traders who want clearer rules around context, entries, invalidation and execution.",
        "Swing, Trend & Indicator Trading": "A practical trend and indicator trading guide for readers who want to connect chart context, confirmation, execution and risk without turning indicators into prediction machines.",
        "Gold, Silver, Forex & Crypto": "A market-specific trading guide for readers who want to understand price behavior, volatility, execution and risk in fast-moving global markets.",
        "AI, Algorithmic & Systematic Trading": "A systematic trading title focused on turning trading ideas into structured, testable and repeatable workflows with disciplined risk control.",
        "Scalping & Day Trading": "A practical intraday trading title for readers who want sharper session context, faster decision structure and disciplined execution under short time horizons.",
        "Trading Risk, Execution & Professional Practice": "A professional trading guide centered on risk, execution discipline and the practical realities that separate a trading idea from a survivable process.",
        "Start Here & Core Technical Analysis": "A practical technical-analysis guide for traders who want clearer chart reading, more structured decisions and a stronger connection between setup logic, invalidation and risk."
    }
    return by_category.get(category, "A practical trading guide designed to help traders build clearer, more structured and risk-aware decisions.")

def shorten(text: str, limit=700) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stops = [cut.rfind(". "), cut.rfind("! "), cut.rfind("? ")]
    stop = max(stops)
    if stop > int(limit * .55):
        return cut[:stop + 1]
    return cut.rsplit(" ", 1)[0] + "…"

def parse_book(path: Path):
    source = path.read_text(encoding="utf-8", errors="ignore")
    schema = find_book_schema(source)
    if not schema:
        return None

    title = clean_text(str(schema.get("name", "")))
    subtitle = clean_text(str(schema.get("alternateName", "")))
    genre = clean_text(str(schema.get("genre", "")))
    language = clean_text(str(schema.get("inLanguage", "en")))
    google_id = extract_google_id(schema, source)
    if not title or not google_id:
        return None

    google_url = str(schema.get("sameAs", "")).strip()
    if "play.google.com/store/books/details" not in google_url:
        google_url = f"https://play.google.com/store/books/details?id={google_id}"
    preview_url = f"https://play.google.com/books/reader?id={google_id}&hl=en"

    image = schema.get("image", "")
    if isinstance(image, dict):
        cover = str(image.get("contentUrl") or image.get("url") or "")
    else:
        cover = str(image or "")
    if not cover:
        cover = f"https://books.google.com/books/content?id={google_id}&printsec=frontcover&img=1&zoom=2&source=gbs_api"

    tags = about_names(schema)
    tags += re.findall(r'<meta\s+property=["\']book:tag["\']\s+content=["\']([^"\']+)["\']', source, flags=re.I)
    seen = set()
    tags = [x for x in tags if x and not (x.lower() in seen or seen.add(x.lower()))]

    about = first_about_paragraph(source)
    schema_desc = clean_text(str(schema.get("description", "")))
    meta_desc = meta(source, "description")
    description = shorten(about or schema_desc or meta_desc)

    medium = extract_medium(schema, source)
    canonical = str(schema.get("url", "")).strip() or f"https://faramarzkowsari.github.io/books/{path.parent.name}/"
    search_blob = " ".join([title, subtitle, genre, description, " ".join(tags)])

    book = {
        "title": title,
        "subtitle": subtitle,
        "genre": genre,
        "language": language,
        "google_id": google_id,
        "google_url": google_url,
        "preview_url": preview_url,
        "cover": cover,
        "medium_url": medium,
        "source_page": canonical,
        "description": description,
        "tags": tags[:10],
        "search_blob": search_blob,
    }
    if not is_trading_book(book):
        return None
    book["category"] = category_for(book)
    placeholder_markers = [
        "pending source-book review",
        "full editorial description will be added",
        "editorial summary pending",
        "to be completed",
        "structurally ready"
    ]
    if len(book["description"]) < 80 or any(x in book["description"].lower() for x in placeholder_markers):
        book["description"] = promotional_fallback(book["title"], book["category"])
        book["search_blob"] = " ".join([book["title"], book["subtitle"], book["genre"], book["description"], " ".join(book["tags"])])
    return book

def esc(value):
    return html.escape(str(value), quote=True)

def slugify(value: str):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value

def render_card(book: dict) -> str:
    tags = book["tags"][:5]
    if not tags:
        tags = [book["category"], "Trading"]
    tag_html = "".join(f"<span>{esc(t)}</span>" for t in tags)
    medium_badge = '<span class="medium-badge">Medium article</span>' if book["medium_url"] else ""
    medium_link = ""
    if book["medium_url"]:
        medium_link = f'<a class="medium" href="{esc(book["medium_url"])}" target="_blank" rel="noopener noreferrer">Read the Medium article</a>'

    searchable = " ".join([
        book["title"], book["subtitle"], book["category"], book["description"], " ".join(book["tags"])
    ])
    return f'''<article class="book-card" data-category="{esc(slugify(book["category"]))}" data-search="{esc(searchable)}">
  <a class="book-cover-link" href="{esc(book["google_url"])}" target="_blank" rel="noopener noreferrer" aria-label="Open {esc(book["title"])} on Google Books">
    <img class="book-cover" src="{esc(book["cover"])}" alt="Book cover of {esc(book["title"])} by Faramarz Kowsari" loading="lazy" decoding="async">
  </a>
  <div class="book-content">
    <div class="card-topline"><span class="category-badge">{esc(book["category"])}</span>{medium_badge}</div>
    <h3>{esc(book["title"])}</h3>
    {f'<p class="subtitle">{esc(book["subtitle"])}</p>' if book["subtitle"] else ''}
    <p class="description">{esc(book["description"])}</p>
    <div class="keyword-row">{tag_html}</div>
    <div class="card-actions">
      <a class="buy" href="{esc(book["google_url"])}" target="_blank" rel="noopener noreferrer">View / Buy on Google Books</a>
      <a class="preview" href="{esc(book["preview_url"])}" target="_blank" rel="noopener noreferrer">Read the Free Preview on Google Books</a>
      <a class="details" href="{esc(book["source_page"])}">Book details &amp; full description</a>
      {medium_link}
    </div>
  </div>
</article>'''

def render_category_page(category: str, books: list[dict], updated: str) -> str:
    slug = CATEGORY_PAGE_SLUGS[category]
    title = CATEGORY_SEARCH_TITLES[category]
    canonical = f"https://faramarzkowsari.github.io/trading-books/{slug}/"
    description = CATEGORY_LONG_INTROS[category]
    cards = "\n".join(render_card(b) for b in books)
    other_links = "\n".join(
        f'<a href="../{CATEGORY_PAGE_SLUGS[c]}/">{esc(CATEGORY_SEARCH_TITLES[c])}</a>'
        for c in CATEGORY_ORDER if c != category
    )
    items = [{
        "@type": "ListItem",
        "position": i,
        "item": {
            "@type": "Book",
            "name": b["title"],
            "author": {"@type": "Person", "name": "Faramarz Kowsari"},
            "url": b["google_url"],
            "image": b["cover"],
        }
    } for i, b in enumerate(books, 1)]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#collection",
                "name": title,
                "url": canonical,
                "description": description,
                "inLanguage": "en",
                "author": {"@type": "Person", "@id": "https://faramarzkowsari.github.io/#person", "name": "Faramarz Kowsari"},
                "isPartOf": {"@id": "https://faramarzkowsari.github.io/trading-books/#collection"},
                "mainEntity": {"@type": "ItemList", "numberOfItems": len(books), "itemListElement": items},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Trading Books", "item": "https://faramarzkowsari.github.io/trading-books/"},
                    {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<title>{esc(title)} | Faramarz Kowsari</title>
<meta name="description" content="{esc(shorten(description, 250))}">
<link rel="canonical" href="{canonical}">
<link rel="sitemap" type="application/xml" href="../sitemap.xml">
<link rel="author" href="https://faramarzkowsari.github.io/books/author/">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(shorten(description, 240))}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://i.pinimg.com/736x/c7/ae/da/c7aeda0a3132f7d85ebd6af24e02cdc2.jpg">
<meta property="og:image:width" content="736"><meta property="og:image:height" content="386"><meta property="og:image:type" content="image/jpeg">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(shorten(description, 200))}">
<meta name="twitter:image" content="https://i.pinimg.com/736x/c7/ae/da/c7aeda0a3132f7d85ebd6af24e02cdc2.jpg">
<link rel="stylesheet" href="../styles.css?v=20261102-4">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-B8XLF16YDW"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-B8XLF16YDW');</script>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>
</head><body>
<main class="category-landing">
<nav class="landing-crumbs"><a href="../">Trading Books</a> › <span>{esc(title)}</span></nav>
<header class="category-hero"><p class="section-kicker">FARAMARZ KOWSARI · TRADING BOOKS</p><h1>{esc(title)}</h1><p>{esc(description)}</p><p><strong>{len(books)} books in this collection.</strong> Every cover links directly to Google Books, and each title includes a free-preview link when available.</p></header>
<section class="book-section"><div class="book-grid">{cards}</div></section>
<section class="category-context"><h2>Where this category fits in a trading education</h2><p>{esc(CATEGORY_BLURBS[category])} Use this page when this subject matches a real weakness in your process; use the complete library when you need to compare several approaches before choosing what to study next.</p><p><a class="button button-primary" href="../">Explore all trading books</a></p></section>
<nav class="related-category-links" aria-label="Other trading book categories"><h2>Explore related trading-book collections</h2><div class="seo-category-grid">{other_links}</div></nav>
</main>
<footer><p><strong>Faramarz Kowsari Trading Books</strong> · Category updated {updated}</p><p class="disclaimer">Educational material only. Trading and investing involve risk.</p></footer>
</body></html>'''

def build():
    books = []
    for path in sorted(BOOKS.glob("*/index.html")):
        book = parse_book(path)
        if book:
            books.append(book)

    books.sort(key=lambda b: (CATEGORY_ORDER.index(b["category"]) if b["category"] in CATEGORY_ORDER else 999, b["title"].lower()))
    grouped = defaultdict(list)
    for book in books:
        grouped[book["category"]].append(book)

    category_nav = []
    category_links = []
    sections = []
    for category in CATEGORY_ORDER:
        items = grouped.get(category, [])
        if not items:
            continue
        sid = slugify(category)
        category_nav.append(f'<button class="category-filter" type="button" data-filter="{esc(sid)}">{esc(category)} <span>{len(items)}</span></button>')
        category_links.append(f'<a class="seo-category-card" href="./{CATEGORY_PAGE_SLUGS[category]}/"><strong>{esc(CATEGORY_SEARCH_TITLES[category])}</strong><span>{len(items)} books</span><small>{esc(CATEGORY_BLURBS[category])}</small></a>')
        cards = "\n".join(render_card(b) for b in items)
        sections.append(f'''<section class="book-section" id="{esc(sid)}" data-category-section="{esc(sid)}">
  <div class="section-heading">
    <div><p class="section-kicker">{len(items)} BOOK{"S" if len(items) != 1 else ""}</p><h2>{esc(category)}</h2></div>
    <p>{esc(CATEGORY_BLURBS.get(category, ""))}</p>
  </div>
  <div class="book-grid">{cards}</div>
</section>''')

    item_list = []
    for pos, book in enumerate(books, 1):
        item_list.append({
            "@type": "ListItem",
            "position": pos,
            "item": {
                "@type": "Book",
                "name": book["title"],
                "alternateName": book["subtitle"] or None,
                "author": {"@type": "Person", "name": "Faramarz Kowsari"},
                "genre": book["genre"] or "Trading",
                "inLanguage": book["language"] or "en",
                "url": book["google_url"],
                "sameAs": book["google_url"],
                "image": book["cover"],
            }
        })

    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": "https://faramarzkowsari.github.io/trading-books/#collection",
        "name": "Trading Books for Beginners & Active Traders",
        "url": "https://faramarzkowsari.github.io/trading-books/",
        "description": "A dedicated trading-book showcase covering futures, options, order flow, Smart Money Concepts, technical analysis, price action, scalping, swing trading, gold, forex, crypto, risk management and algorithmic trading.",
        "author": {"@type": "Person", "@id": "https://faramarzkowsari.github.io/#person", "name": "Faramarz Kowsari", "url": "https://faramarzkowsari.github.io/books/author/", "sameAs": ["https://orcid.org/0000-0003-1692-0453", "https://github.com/FaramarzKowsari", "https://www.linkedin.com/in/faramarzkowsari"]},
        "about": [{"@type": "Thing", "name": x} for x in ["Trading", "Technical Analysis", "Futures Trading", "Options Trading", "Order Flow", "Smart Money Concepts", "Price Action", "Risk Management", "Algorithmic Trading"]],
        "hasPart": [{"@type": "CollectionPage", "name": CATEGORY_SEARCH_TITLES[c], "url": f"https://faramarzkowsari.github.io/trading-books/{CATEGORY_PAGE_SLUGS[c]}/"} for c in CATEGORY_ORDER if grouped.get(c)],
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(books), "itemListElement": item_list}
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://faramarzkowsari.github.io/"},
            {"@type": "ListItem", "position": 2, "name": "Trading Books", "item": "https://faramarzkowsari.github.io/trading-books/"}
        ]
    }
    faq = {
        "@context":"https://schema.org",
        "@type":"FAQPage",
        "mainEntity":[
            {"@type":"Question","name":"Can I preview the trading books before buying?","acceptedAnswer":{"@type":"Answer","text":"Yes. Each title includes a Read the Free Preview on Google Books link whenever the Google Books reader is available."}},
            {"@type":"Question","name":"What trading subjects are covered?","acceptedAnswer":{"@type":"Answer","text":"The collection covers technical analysis, price action, market structure, Smart Money Concepts, order flow, futures, options, volatility, scalping, day trading, swing trading, gold, forex, crypto, risk management, execution, backtesting and algorithmic or AI-assisted trading."}},
            {"@type":"Question","name":"Where can I buy the books?","acceptedAnswer":{"@type":"Answer","text":"Book covers and purchase buttons link directly to the corresponding title on Google Books."}}
        ]
    }
    jsonld_html = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False, separators=(",", ":")) + '</script>\n' + '<script type="application/ld+json">' + json.dumps(breadcrumb, ensure_ascii=False, separators=(",", ":")) + '</script>\n' + '<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False, separators=(",", ":")) + '</script>'

    template = TEMPLATE.read_text(encoding="utf-8")
    updated = datetime.now(timezone.utc).date().isoformat()
    rendered = (template
        .replace("{{BOOK_COUNT}}", str(len(books)))
        .replace("{{CATEGORY_COUNT}}", str(sum(1 for c in CATEGORY_ORDER if grouped.get(c))))
        .replace("{{UPDATED_DATE}}", updated)
        .replace("<!-- GENERATED:JSONLD -->", jsonld_html)
        .replace("<!-- GENERATED:CATEGORY_NAV -->", "\n".join(category_nav))
        .replace("<!-- GENERATED:CATEGORY_LINKS -->", "\n".join(category_links))
        .replace("<!-- GENERATED:BOOK_SECTIONS -->", "\n".join(sections))
    )

    SHOWCASE.mkdir(parents=True, exist_ok=True)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(rendered, encoding="utf-8")

    generated_urls = ["https://faramarzkowsari.github.io/trading-books/"]
    for category in CATEGORY_ORDER:
        items = grouped.get(category, [])
        if not items:
            continue
        slug = CATEGORY_PAGE_SLUGS[category]
        out_dir = SHOWCASE / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render_category_page(category, items, updated), encoding="utf-8")
        generated_urls.append(f"https://faramarzkowsari.github.io/trading-books/{slug}/")

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in generated_urls:
        sitemap.append(f'  <url><loc>{url}</loc><lastmod>{updated}</lastmod></url>')
    sitemap.append('</urlset>')
    (SHOWCASE / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(books),
        "categories": {c: len(grouped[c]) for c in CATEGORY_ORDER if grouped.get(c)},
        "books": books,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(books)} trading books across {len(payload['categories'])} categories.")

if __name__ == "__main__":
    build()
