#!/usr/bin/env python3
"""Build and apply durable semantic SEO metadata for the books library.

Two phases are intentionally separated:
  prepare
    - runs after build_books.py has merged source reviews
    - derives a semantic search profile for every active book
    - writes books/seo-keywords.json and embeds the profile in books/books.json
  apply
    - runs after localized discovery pages are generated
    - enriches Book/WebPage JSON-LD, breadcrumbs and internal links
    - creates crawlable topic hubs and links the thematic index to them

The script deliberately does NOT emit the legacy meta keywords tag. Google ignores
that tag. Search concepts instead live in visible editorial content, internal
links, JSON-LD keywords/about, machine-readable catalog data, and topic hubs.
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
SEO_DATA = BOOKS / "seo-keywords.json"
TOPICS = BOOKS / "topics"
SITE = "https://faramarzkowsari.github.io"
BOOKS_BASE = f"{SITE}/books"
AUTHOR = "Faramarz Kowsari"

EMPTY = ("", None, [], {})
LOCALE_PATHS = {"en":"","ru":"ru","tr":"tr","de":"de","es":"es","fr":"fr","pt-BR":"pt-br"}
LANG_CODES = {
    "English":"en","Türkçe":"tr","Turkish":"tr","Deutsch":"de","German":"de",
    "Español":"es","Spanish":"es","Français":"fr","French":"fr",
    "Português":"pt","Portuguese":"pt","Português (Brasil)":"pt-BR","Brazilian Portuguese":"pt-BR",
    "Русский":"ru","Russian":"ru","فارسی":"fa","Persian":"fa","العربية":"ar","Arabic":"ar",
    "Bahasa Indonesia":"id","Indonesian":"id","Tiếng Việt":"vi","Vietnamese":"vi",
    "ไทย":"th","Thai":"th","বাংলা":"bn","Bengali":"bn","Romanian":"ro","Română":"ro",
}
STOPWORDS = {
    "a","an","and","are","as","at","be","by","for","from","how","in","into","is","it",
    "of","on","or","the","this","to","through","using","with","your","guide","book",
    "trading","faramarz","kowsari","practical","complete","modern","new","why",
}

CLUSTERS = [
    {"slug":"order-flow-trading","label":"Order Flow & Market Microstructure",
     "terms":("order flow","depth of market","dom","volume bubbles","footprint","cvd","cumulative volume delta","delta","absorption","market microstructure","tape reading","time and sales","volume profile"),
     "description":"Books in this hub focus on the mechanics behind visible price movement: executed volume, resting liquidity, aggression, absorption, queue behavior, footprint data and other order-flow evidence. The emphasis is on reading what actually traded and how price responded, rather than treating a single indicator or large print as a prediction.",
     "query_examples":["order flow trading books","DOM trading and market depth","volume delta and CVD trading","absorption and footprint trading","market microstructure for traders"]},
    {"slug":"smart-money-trading","label":"Smart Money Concepts & Intraday Structure",
     "terms":("smart money","ict","fair value gap","order block","breaker block","balanced price range","bpr","liquidity sweep","inducement","silver bullet","turtle soup","smt divergence","dealing range","opening range gap","first hour dealing range","kill zone"),
     "description":"This hub brings together books on liquidity, dealing ranges, imbalances, fair value gaps, order blocks and related Smart Money Concepts. The pages are organized around explicit definitions, market structure, invalidation and testable intraday workflows rather than hindsight labels.",
     "query_examples":["smart money concepts books","ICT trading concepts","fair value gap and order block trading","liquidity sweep trading","intraday dealing range trading"]},
    {"slug":"options-volatility-trading","label":"Options, Gamma & Volatility Trading",
     "terms":("0dte","options","gamma exposure","gex","gamma flip","dealer positioning","call wall","put wall","vanna","charm","volatility","implied volatility"),
     "description":"Books in this group cover options mechanics, same-day expiration, Gamma Exposure, dealer-positioning models, volatility and the ways option-derived context can interact with intraday market structure. Model assumptions, execution risk and live-market confirmation remain central.",
     "query_examples":["0DTE options trading books","gamma exposure GEX trading","Gamma Flip Call Wall Put Wall","options volatility trading","dealer positioning and market structure"]},
    {"slug":"algorithmic-ai-trading","label":"Algorithmic & AI Trading",
     "terms":("ai trading","trading agent","trading bot","algorithmic trading","machine learning trading","automated trading","quantitative trading","decision-native"),
     "description":"This hub covers AI-assisted, algorithmic and agentic trading workflows, including data, model decisions, risk controls, execution architecture, testing and production reliability. AI is treated as one component inside a governed trading system rather than as a source of guaranteed signals.",
     "query_examples":["AI trading books","algorithmic trading systems","AI trading agents and bots","machine learning for trading","automated trading risk controls"]},
    {"slug":"trading-markets","label":"Trading & Financial Markets",
     "terms":("trading","scalping","forex","futures","crypto futures","funded trader","market structure","vwap","volume profile","risk management","technical analysis"),
     "description":"A broad trading hub for books on market structure, execution, session behavior, risk, technical tools and repeatable decision processes. Specialized order-flow, options and Smart Money titles are linked to their more focused hubs when appropriate.",
     "query_examples":["trading books","futures trading guide","intraday trading books","market structure trading","trading risk management"]},
    {"slug":"artificial-intelligence","label":"Artificial Intelligence",
     "terms":("artificial intelligence","generative ai","llm","large language model","ai agent","multimodal ai","rag","retrieval augmented generation","ai api"),
     "description":"Books in this hub explain artificial intelligence systems, generative models, agents, multimodal workflows, retrieval, evaluation, governance and real-world use. The collection emphasizes useful system design, limitations and responsible human oversight.",
     "query_examples":["artificial intelligence books","generative AI practical guide","AI agents books","RAG and multimodal AI","AI systems and governance"]},
    {"slug":"prompt-engineering","label":"Prompt Engineering & Applied AI",
     "terms":("prompt engineering","prompt","chatgpt","claude","gemini","prompt library","ai prompts"),
     "description":"This hub collects practical books on prompt engineering and reusable AI workflows for business, marketing, research, education and other domains. Prompts are framed as structured decision and work templates rather than magical phrases.",
     "query_examples":["prompt engineering books","AI prompt library","ChatGPT prompts for business","applied AI prompts","prompt design guide"]},
    {"slug":"machine-learning-data","label":"Machine Learning & Data",
     "terms":("machine learning","deep learning","data science","sql","data analysis","analytics","python","interview","neural network"),
     "description":"Books in this cluster cover machine learning, data analysis, technical interviews, algorithms and practical engineering reasoning. The emphasis is on concepts, visual intuition, reproducible workflows and real-world systems.",
     "query_examples":["machine learning books","data science practical guide","machine learning interview questions","SQL and data analysis","deep learning concepts"]},
    {"slug":"software-technology","label":"Software, APIs & Technology",
     "terms":("software","api","developer","programming","web development","technology","architecture","engineering","cybersecurity"),
     "description":"A technology hub for software architecture, APIs, engineering workflows and modern technical systems. The books connect concepts to implementation choices, tradeoffs, reliability and practical use.",
     "query_examples":["software engineering books","API engineering guide","software architecture books","technology practical guide","developer reference books"]},
    {"slug":"business-marketing","label":"Business, Marketing & Entrepreneurship",
     "terms":("business","marketing","sales","e-commerce","ecommerce","entrepreneur","small business","customer","social media"),
     "description":"Books in this hub address business strategy, marketing, sales, customer evidence, e-commerce, entrepreneurship and AI-assisted workflows. The focus is on decisions, repeatable processes and practical implementation.",
     "query_examples":["business strategy books","marketing books","AI for small business","e-commerce guide","social media marketing prompts"]},
    {"slug":"finance-economics","label":"Money, Finance & Economics",
     "terms":("personal finance","finance","money","wealth","debt","economics","economic","financial life","investing"),
     "description":"This hub groups books about money decisions, personal finance, economic reasoning, debt, risk and financial behavior. Titles are organized around practical understanding rather than promises of wealth or guaranteed outcomes.",
     "query_examples":["personal finance books","money psychology books","economics for everyday life","debt and financial decisions","financial behavior guide"]},
    {"slug":"psychology-personal-growth","label":"Psychology, Mindfulness & Personal Growth",
     "terms":("psychology","mindfulness","personal growth","self-help","meditation","zen","habit","motivation","relationship","mental"),
     "description":"Books in this collection explore psychology, mindfulness, relationships, habits, attention and personal development. The focus is on clearer understanding, reflection and practical application.",
     "query_examples":["psychology and personal growth books","mindfulness books","habit and motivation books","relationship psychology books","Zen and meditation books"]},
    {"slug":"language-learning","label":"Language Learning & Test Preparation",
     "terms":("language","turkish","grammar","vocabulary","ielts","english","test preparation","speaking","writing","reading","listening"),
     "description":"This hub covers language learning, visual grammar and exam preparation. It includes structured learning books, multilingual editions and visual review resources designed to make high-volume material easier to navigate.",
     "query_examples":["language learning books","Turkish grammar books","IELTS preparation books","English test preparation","visual grammar guide"]},
    {"slug":"literature-classics","label":"Literature, Poetry & Classics",
     "terms":("literature","poetry","poem","classic","fiction","novel","shahnameh","rumi","hafez","khayyam"),
     "description":"A literary hub for poetry, classics, reinterpretations and reading-oriented works. Related titles are grouped by literary subject rather than by technical category.",
     "query_examples":["classic literature books","poetry books","Persian literature books","Rumi Hafez Khayyam books","literary classics"]},
    {"slug":"safety-resilience","label":"Safety, Climate & Resilience",
     "terms":("weather","heat","air quality","earthquake","disaster","survival","resilience","safety","climate"),
     "description":"Books in this hub cover practical risk awareness, climate, safety, resilience and preparation. The focus is on understandable frameworks and actionable planning rather than alarmism.",
     "query_examples":["resilience and safety books","disaster preparedness books","climate risk guide","earthquake preparedness","air quality and heat safety"]},
]

CATEGORY_LOCALIZATION = {
    "en":{"trading":"trading and financial markets","ai":"artificial intelligence","business":"business and marketing","data":"machine learning and data","finance":"personal finance and economics","psychology":"psychology and personal growth","language":"language learning","technology":"software and technology","default":"practical nonfiction"},
    "tr":{"trading":"trading ve finansal piyasalar","ai":"yapay zekâ","business":"işletme ve pazarlama","data":"makine öğrenmesi ve veri","finance":"kişisel finans ve ekonomi","psychology":"psikoloji ve kişisel gelişim","language":"dil öğrenimi","technology":"yazılım ve teknoloji","default":"uygulamalı kitaplar"},
    "ru":{"trading":"трейдинг и финансовые рынки","ai":"искусственный интеллект","business":"бизнес и маркетинг","data":"машинное обучение и данные","finance":"личные финансы и экономика","psychology":"психология и личное развитие","language":"изучение языков","technology":"программное обеспечение и технологии","default":"практические книги"},
    "de":{"trading":"Trading und Finanzmärkte","ai":"Künstliche Intelligenz","business":"Business und Marketing","data":"Machine Learning und Daten","finance":"Finanzen und Wirtschaft","psychology":"Psychologie und persönliche Entwicklung","language":"Sprachenlernen","technology":"Software und Technologie","default":"Praxisbücher"},
    "es":{"trading":"trading y mercados financieros","ai":"inteligencia artificial","business":"negocios y marketing","data":"aprendizaje automático y datos","finance":"finanzas personales y economía","psychology":"psicología y desarrollo personal","language":"aprendizaje de idiomas","technology":"software y tecnología","default":"libros prácticos"},
    "fr":{"trading":"trading et marchés financiers","ai":"intelligence artificielle","business":"entreprise et marketing","data":"machine learning et données","finance":"finances personnelles et économie","psychology":"psychologie et développement personnel","language":"apprentissage des langues","technology":"logiciels et technologie","default":"livres pratiques"},
    "pt-BR":{"trading":"trading e mercados financeiros","ai":"inteligência artificial","business":"negócios e marketing","data":"machine learning e dados","finance":"finanças pessoais e economia","psychology":"psicologia e desenvolvimento pessoal","language":"aprendizado de idiomas","technology":"software e tecnologia","default":"livros práticos"},
}
RELATED_COPY = {
    "en":("Related books","Explore closely related titles in the same subject area.","Explore the topic hub"),
    "tr":("İlgili kitaplar","Aynı konu alanındaki yakından ilişkili kitapları keşfedin.","Konu merkezini keşfet"),
    "ru":("Похожие книги","Посмотрите близкие по теме книги из той же предметной области.","Открыть тематический раздел"),
    "de":("Verwandte Bücher","Entdecken Sie eng verwandte Titel aus demselben Themenbereich.","Themen-Hub öffnen"),
    "es":("Libros relacionados","Explora títulos estrechamente relacionados del mismo tema.","Abrir el centro temático"),
    "fr":("Livres associés","Découvrez des titres étroitement liés dans le même domaine.","Ouvrir le hub thématique"),
    "pt-BR":("Livros relacionados","Explore títulos diretamente relacionados ao mesmo tema.","Abrir o hub temático"),
}
BOOK_WORD={"en":"book","tr":"kitap","ru":"книга","de":"Buch","es":"libro","fr":"livre","pt-BR":"livro"}
GUIDE_WORD={"en":"guide","tr":"rehberi","ru":"руководство","de":"Leitfaden","es":"guía","fr":"guide","pt-BR":"guia","fa":"راهنما","ar":"دليل","id":"panduan","vi":"hướng dẫn","th":"คู่มือ","bn":"গাইড","ro":"ghid","fil":"gabay"}
BOOK_WORD.update({"fa":"کتاب","ar":"كتاب","id":"buku","vi":"sách","th":"หนังสือ","bn":"বই","ro":"carte","fil":"aklat"})
CATEGORY_LOCALIZATION.update({
    "fa":{"trading":"معامله‌گری و بازارهای مالی","ai":"هوش مصنوعی","business":"کسب‌وکار و بازاریابی","data":"یادگیری ماشین و داده","finance":"مالی شخصی و اقتصاد","psychology":"روان‌شناسی و رشد فردی","language":"یادگیری زبان","technology":"نرم‌افزار و فناوری","default":"کتاب‌های کاربردی"},
    "ar":{"trading":"التداول والأسواق المالية","ai":"الذكاء الاصطناعي","business":"الأعمال والتسويق","data":"تعلم الآلة والبيانات","finance":"التمويل الشخصي والاقتصاد","psychology":"علم النفس والتنمية الشخصية","language":"تعلم اللغات","technology":"البرمجيات والتكنولوجيا","default":"كتب عملية"},
    "id":{"trading":"trading dan pasar keuangan","ai":"kecerdasan buatan","business":"bisnis dan pemasaran","data":"machine learning dan data","finance":"keuangan pribadi dan ekonomi","psychology":"psikologi dan pengembangan diri","language":"pembelajaran bahasa","technology":"perangkat lunak dan teknologi","default":"buku praktis"},
    "vi":{"trading":"giao dịch và thị trường tài chính","ai":"trí tuệ nhân tạo","business":"kinh doanh và tiếp thị","data":"học máy và dữ liệu","finance":"tài chính cá nhân và kinh tế","psychology":"tâm lý học và phát triển bản thân","language":"học ngôn ngữ","technology":"phần mềm và công nghệ","default":"sách thực hành"},
    "th":{"trading":"การเทรดและตลาดการเงิน","ai":"ปัญญาประดิษฐ์","business":"ธุรกิจและการตลาด","data":"แมชชีนเลิร์นนิงและข้อมูล","finance":"การเงินส่วนบุคคลและเศรษฐศาสตร์","psychology":"จิตวิทยาและการพัฒนาตนเอง","language":"การเรียนภาษา","technology":"ซอฟต์แวร์และเทคโนโลยี","default":"หนังสือเชิงปฏิบัติ"},
    "bn":{"trading":"ট্রেডিং ও আর্থিক বাজার","ai":"কৃত্রিম বুদ্ধিমত্তা","business":"ব্যবসা ও মার্কেটিং","data":"মেশিন লার্নিং ও ডেটা","finance":"ব্যক্তিগত অর্থ ও অর্থনীতি","psychology":"মনোবিজ্ঞান ও ব্যক্তিগত উন্নয়ন","language":"ভাষা শিক্ষা","technology":"সফটওয়্যার ও প্রযুক্তি","default":"ব্যবহারিক বই"},
    "ro":{"trading":"trading și piețe financiare","ai":"inteligență artificială","business":"afaceri și marketing","data":"machine learning și date","finance":"finanțe personale și economie","psychology":"psihologie și dezvoltare personală","language":"învățarea limbilor","technology":"software și tehnologie","default":"cărți practice"},
    "fil":{"trading":"trading at financial markets","ai":"artificial intelligence","business":"negosyo at marketing","data":"machine learning at data","finance":"personal finance at ekonomiya","psychology":"sikolohiya at personal growth","language":"pag-aaral ng wika","technology":"software at teknolohiya","default":"praktikal na aklat"}
})

SEO_START="<!-- semantic-seo:start -->"
SEO_END="<!-- semantic-seo:end -->"
RELATED_START="<!-- semantic-related-books:start -->"
RELATED_END="<!-- semantic-related-books:end -->"
HUBS_START="<!-- semantic-topic-hubs:start -->"
HUBS_END="<!-- semantic-topic-hubs:end -->"
SCRIPT_RE=re.compile(r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',re.I|re.S)

def load_json(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,OSError):return default

def clean(value):return re.sub(r"\s+"," ",str(value or "")).strip()
def esc(value):return html.escape(str(value or ""),quote=True)

def unique(items):
    out=[];seen=set()
    for raw in items:
        value=clean(raw);key=value.casefold()
        if not value or key in seen:continue
        seen.add(key);out.append(value)
    return out

def compact_terms(text):
    words=re.findall(r"[A-Za-z0-9][A-Za-z0-9+.#/&-]*",clean(text).lower())
    return [w for w in words if len(w)>2 and w not in STOPWORDS]

def search_text(book):
    fields=[book.get("title"),book.get("subtitle"),book.get("category")]
    fields.extend(book.get("key_topics") or [])
    return " ".join(clean(x).lower() for x in fields if clean(x))

def cluster_for(book):
    hay=search_text(book)
    scored=[]
    for priority,cluster in enumerate(CLUSTERS):
        matched=[term for term in cluster["terms"] if term in hay]
        if not matched:continue
        # Prefer the cluster supported by the largest number of controlled terms.
        # Longer phrase matches carry slightly more weight than generic one-word hits.
        score=sum(2 if " " in term else 1 for term in matched)
        scored.append((score,-priority,cluster))
    if scored:
        scored.sort(key=lambda row:(-row[0],-row[1]))
        return scored[0][2]
    return {"slug":"other-books","label":"Other Books","description":"Additional books in the Faramarz Kowsari library that do not yet belong to a larger dedicated topic hub.","query_examples":["Faramarz Kowsari books","practical nonfiction books"],"terms":()}

def broad_category(book):
    hay=" "+search_text(book)+" "
    rules=[
        ("trading",("trading","futures","forex","options","market","vwap","liquidity","order flow","scalping","gex")),
        ("ai",("artificial intelligence"," ai ","prompt","chatgpt","llm","agent","generative ai")),
        ("data",("machine learning","data science","sql","python","analytics","deep learning")),
        ("business",("business","marketing","sales","e-commerce","ecommerce","entrepreneur")),
        ("finance",("finance","money","wealth","debt","econom")),
        ("psychology",("psychology","mindfulness","personal growth","relationship","habit","zen")),
        ("language",("language","turkish","grammar","ielts","vocabulary")),
        ("technology",("software","api","developer","programming","technology","architecture")),
    ]
    for key,terms in rules:
        if any(t in hay for t in terms):return key
    return "default"

def base_entities(book):
    topics=[clean(x) for x in (book.get("key_topics") or []) if clean(x)]
    subtitle=clean(book.get("subtitle"));chunks=[]
    if subtitle:chunks=[clean(x) for x in re.split(r"[,;:|•—]+",subtitle) if 2<=len(clean(x).split())<=7]
    entities=unique(topics+chunks)
    if not entities:entities=unique([clean(book.get("category")),clean(book.get("title"))])
    return entities[:20]

def localized_queries(book,locale,entities):
    title=clean(book.get("title")) or clean(book.get("slug")).replace("-"," ").title()
    key=broad_category(book)
    category=CATEGORY_LOCALIZATION.get(locale,CATEGORY_LOCALIZATION["en"]).get(key,CATEGORY_LOCALIZATION.get(locale,CATEGORY_LOCALIZATION["en"])["default"])
    book_word=BOOK_WORD.get(locale,"book");guide_word=GUIDE_WORD.get(locale,"guide")
    topic=entities[0] if entities else clean(book.get("category")) or title
    if locale=="tr":
        secondary=[f"{title} {book_word}",f"{category} {book_word}",f"{topic} {guide_word}",topic]
        long_tail=[f"{topic} nasıl çalışır",f"{topic} için uygulamalı {guide_word}",f"{title} Faramarz Kowsari"]
    elif locale=="ru":
        secondary=[f"{title} {book_word}",f"{book_word} о {category}",f"{guide_word} по {topic}",topic]
        long_tail=[f"как работает {topic}",f"практическое руководство по {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="de":
        secondary=[f"{title} {book_word}",f"{category} {book_word}",f"{topic} {guide_word}",topic]
        long_tail=[f"wie funktioniert {topic}",f"praktischer {guide_word} zu {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="es":
        secondary=[f"{title} {book_word}",f"{book_word} de {category}",f"{guide_word} de {topic}",topic]
        long_tail=[f"cómo funciona {topic}",f"{guide_word} práctica de {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="fr":
        secondary=[f"{title} {book_word}",f"{book_word} sur {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"comment fonctionne {topic}",f"{guide_word} pratique de {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="pt-BR":
        secondary=[f"{title} {book_word}",f"{book_word} sobre {category}",f"{guide_word} de {topic}",topic]
        long_tail=[f"como funciona {topic}",f"{guide_word} prático de {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="fa":
        secondary=[f"{title} {book_word}",f"{book_word} {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"{topic} چیست",f"{guide_word} کاربردی {topic}",f"{title} فرامرز کوثری"]
    elif locale=="ar":
        secondary=[f"{title} {book_word}",f"{book_word} عن {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"ما هو {topic}",f"{guide_word} عملي عن {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="id":
        secondary=[f"{title} {book_word}",f"{book_word} {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"cara kerja {topic}",f"{guide_word} praktis {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="vi":
        secondary=[f"{title} {book_word}",f"{book_word} về {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"{topic} hoạt động như thế nào",f"{guide_word} thực hành {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="th":
        secondary=[f"{title} {book_word}",f"{book_word} {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"{topic} ทำงานอย่างไร",f"{guide_word} {topic} แบบปฏิบัติ",f"{title} Faramarz Kowsari"]
    elif locale=="bn":
        secondary=[f"{title} {book_word}",f"{category} {book_word}",f"{topic} {guide_word}",topic]
        long_tail=[f"{topic} কীভাবে কাজ করে",f"{topic} ব্যবহারিক {guide_word}",f"{title} Faramarz Kowsari"]
    elif locale=="ro":
        secondary=[f"{title} {book_word}",f"{book_word} despre {category}",f"{guide_word} {topic}",topic]
        long_tail=[f"cum funcționează {topic}",f"{guide_word} practic pentru {topic}",f"{title} Faramarz Kowsari"]
    elif locale=="fil":
        secondary=[f"{title} {book_word}",f"{book_word} tungkol sa {category}",f"{guide_word} sa {topic}",topic]
        long_tail=[f"paano gumagana ang {topic}",f"praktikal na {guide_word} sa {topic}",f"{title} Faramarz Kowsari"]
    else:
        secondary=[f"{title} {book_word}",f"{category} {book_word}",f"{topic} {guide_word}",topic]
        long_tail=[f"how {topic} works",f"practical {guide_word} to {topic}",f"{title} by Faramarz Kowsari"]
    return {"primary_query":title,"secondary_queries":unique(secondary+entities[:6])[:10],"long_tail_queries":unique(long_tail)[:6],"category_phrase":category}

def build_profile(book):
    title=clean(book.get("title")) or clean(book.get("slug")).replace("-"," ").title()
    entities=base_entities(book);cluster=cluster_for(book)
    secondary=unique([f"{title} book",clean(book.get("subtitle")),clean(book.get("category"))]+entities[:10]+([f"{entities[0]} guide"] if entities else []))[:12]
    long_tail=unique([f"{title} by Faramarz Kowsari",f"practical guide to {entities[0]}" if entities else f"{title} practical guide",f"how {entities[0]} works" if entities else f"what is {title}",f"{entities[0]} {entities[1]}" if len(entities)>1 else ""])[:8]
    localized={locale:localized_queries(book,locale,entities) for locale in ("en","tr","ru","de","es","fr","pt-BR","fa","ar","id","vi","th","bn","ro","fil")}
    return {"primary_query":title,"secondary_queries":secondary,"long_tail_queries":long_tail,"entities":entities,"cluster":cluster["slug"],"cluster_label":cluster["label"],"localized":localized}

def related_scores(books,profiles):
    by_slug={clean(b.get("slug")):b for b in books if clean(b.get("slug"))}
    topic_sets={slug:{x.casefold() for x in p.get("entities",[])} for slug,p in profiles.items()}
    token_sets={slug:set(compact_terms(" ".join([clean(by_slug[slug].get("title")),clean(by_slug[slug].get("subtitle")),clean(by_slug[slug].get("category"))]))) for slug in by_slug if slug in profiles}
    for slug,book in by_slug.items():
        if slug not in profiles:continue
        explicit=set(book.get("related_ids") or []);rows=[]
        for other_slug,other in by_slug.items():
            if other_slug==slug or other_slug not in profiles:continue
            score=0
            if clean(other.get("google_books_id")) in explicit:score+=50
            if profiles[slug].get("cluster")==profiles[other_slug].get("cluster"):score+=24
            if clean(book.get("category")).casefold()==clean(other.get("category")).casefold() and clean(book.get("category")):score+=12
            score+=6*len(topic_sets.get(slug,set())&topic_sets.get(other_slug,set()))
            score+=2*len(token_sets.get(slug,set())&token_sets.get(other_slug,set()))
            if score>0:rows.append((score,clean(other.get("title")).casefold(),other_slug))
        rows.sort(key=lambda r:(-r[0],r[1]))
        profiles[slug]["related_slugs"]=[r[2] for r in rows[:5]]

def synthesize_description(book,profile):
    current=clean(book.get("seo_description"))
    if current:return current
    title=clean(book.get("title"));subtitle=clean(book.get("subtitle"));entities=profile.get("entities") or []
    if subtitle:text=f"{title}: {subtitle}. A practical book by Faramarz Kowsari."
    elif entities:text=f"{title} by Faramarz Kowsari explores {', '.join(entities[:4])} with a practical, structured approach."
    else:text=f"{title} by Faramarz Kowsari. Official book page with description, key topics and Google Books access."
    return text[:300]

def prepare():
    books=load_json(DATA,[])
    if not isinstance(books,list):raise SystemExit("books/books.json must contain a JSON array")
    active=[b for b in books if isinstance(b,dict) and clean(b.get("slug")) and b.get("status","active")=="active"]
    profiles={clean(b["slug"]):build_profile(b) for b in active};related_scores(active,profiles)
    for book in books:
        slug=clean(book.get("slug"))
        if slug in profiles:
            book["seo"]=profiles[slug]
            if not clean(book.get("seo_description")):book["seo_description"]=synthesize_description(book,profiles[slug])
    DATA.write_text(json.dumps(books,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SEO_DATA.write_text(json.dumps(profiles,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"Semantic SEO prepare: {len(profiles)} active book profiles generated.")

def page_locale(text):
    m=re.search(r'<html\b[^>]*\blang=["\']([^"\']+)',text,re.I);raw=(m.group(1) if m else "en").replace("_","-")
    if raw.lower()=="pt-br":return "pt-BR"
    base=raw.lower().split("-",1)[0]
    return base if base in {"en","ru","tr","de","es","fr","fa","ar","id","vi","th","bn","ro","fil"} else "en"

def canonical_from(text,fallback):
    m=re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',text,re.I)
    return html.unescape(m.group(1)).strip() if m else fallback

def url_for_slug(slug,locale):
    if locale=="en":return f"{BOOKS_BASE}/{slug}/"
    path_code=LOCALE_PATHS.get(locale,locale.lower());candidate=BOOKS/slug/path_code/"index.html"
    return f"{BOOKS_BASE}/{slug}/{path_code}/" if candidate.exists() else f"{BOOKS_BASE}/{slug}/"

def jsonld_enrich(node,book,profile,locale):
    changed=False
    if isinstance(node,list):
        for item in node:changed|=jsonld_enrich(item,book,profile,locale)
        return changed
    if not isinstance(node,dict):return False
    node_type=node.get("@type");types=node_type if isinstance(node_type,list) else [node_type]
    local=(profile.get("localized") or {}).get(locale,(profile.get("localized") or {}).get("en",{}))
    semantic_keywords=unique([local.get("primary_query")]+list(local.get("secondary_queries") or [])+list(local.get("long_tail_queries") or [])+list(profile.get("entities") or []))[:30]
    if "Book" in types:
        desired={
            "name":clean(book.get("title")) or node.get("name"),
            "alternateName":clean(book.get("subtitle")) or node.get("alternateName"),
            "genre":clean(book.get("category")) or node.get("genre"),
            "keywords":semantic_keywords,
            "about":[{"@type":"Thing","name":x} for x in (profile.get("entities") or [])[:15]],
            "publisher":{"@type":"Person","name":AUTHOR,"url":f"{BOOKS_BASE}/author/"},
            "sameAs":clean(book.get("google_books_url")) or node.get("sameAs"),
        }
        gid=clean(book.get("google_books_id"));doi=clean(book.get("doi"));identifiers=[]
        if gid:identifiers.append({"@type":"PropertyValue","propertyID":"Google Books ID","value":gid})
        if doi:identifiers.append({"@type":"PropertyValue","propertyID":"DOI","value":doi})
        if identifiers:desired["identifier"]=identifiers
        for key,value in desired.items():
            if value not in EMPTY and node.get(key)!=value:node[key]=value;changed=True
    if "WebPage" in types and semantic_keywords and node.get("keywords")!=semantic_keywords:
        node["keywords"]=semantic_keywords;changed=True
    for value in node.values():
        if isinstance(value,(dict,list)):changed|=jsonld_enrich(value,book,profile,locale)
    return changed

def enrich_jsonld(text,book,profile,locale):
    def repl(match):
        try:payload=json.loads(match.group(2).strip())
        except json.JSONDecodeError:return match.group(0)
        if not jsonld_enrich(payload,book,profile,locale):return match.group(0)
        return match.group(1)+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+match.group(3)
    return SCRIPT_RE.sub(repl,text)

def has_schema_type(text,wanted):
    for m in SCRIPT_RE.finditer(text):
        try:payload=json.loads(m.group(2).strip())
        except json.JSONDecodeError:continue
        stack=[payload]
        while stack:
            node=stack.pop()
            if isinstance(node,dict):
                t=node.get("@type")
                if t==wanted or (isinstance(t,list) and wanted in t):return True
                stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
            elif isinstance(node,list):stack.extend(node)
    return False

def source_language(book):
    return clean(book.get("language_code")) or LANG_CODES.get(book.get("language"),"en")

def standalone_book_schema(book,profile,locale,canonical):
    local=(profile.get("localized") or {}).get(locale,(profile.get("localized") or {}).get("en",{}))
    keywords=unique([local.get("primary_query")]+list(local.get("secondary_queries") or [])+list(local.get("long_tail_queries") or [])+list(profile.get("entities") or []))[:30]
    root_url=f"{BOOKS_BASE}/{clean(book.get('slug'))}/"
    payload={
        "@context":"https://schema.org","@type":"Book","@id":root_url+"#book",
        "name":clean(book.get("title")),"author":{"@type":"Person","name":AUTHOR,"url":f"{BOOKS_BASE}/author/"},
        "publisher":{"@type":"Person","name":AUTHOR,"url":f"{BOOKS_BASE}/author/"},
        "inLanguage":source_language(book),"description":clean(book.get("seo_description")) or clean(book.get("summary")),
        "genre":clean(book.get("category")),"keywords":keywords,
        "about":[{"@type":"Thing","name":x} for x in (profile.get("entities") or [])[:15]],
        "url":root_url,"sameAs":clean(book.get("google_books_url")) or root_url,
        "mainEntityOfPage":{"@type":"WebPage","@id":canonical},
    }
    if clean(book.get("subtitle")):payload["alternateName"]=clean(book.get("subtitle"))
    if clean(book.get("cover_url")):payload["image"]=clean(book.get("cover_url"))
    if clean(book.get("published_date")):payload["datePublished"]=clean(book.get("published_date"))
    identifiers=[]
    if clean(book.get("google_books_id")):identifiers.append({"@type":"PropertyValue","propertyID":"Google Books ID","value":clean(book.get("google_books_id"))})
    if clean(book.get("doi")):identifiers.append({"@type":"PropertyValue","propertyID":"DOI","value":clean(book.get("doi"))})
    if identifiers:payload["identifier"]=identifiers
    return payload

def has_breadcrumb_schema(text):
    for m in SCRIPT_RE.finditer(text):
        try:payload=json.loads(m.group(2).strip())
        except json.JSONDecodeError:continue
        stack=[payload]
        while stack:
            item=stack.pop()
            if isinstance(item,dict):
                t=item.get("@type")
                if t=="BreadcrumbList" or (isinstance(t,list) and "BreadcrumbList" in t):return True
                stack.extend(v for v in item.values() if isinstance(v,(dict,list)))
            elif isinstance(item,list):stack.extend(item)
    return False

def breadcrumb_schema(book,profile,locale,canonical):
    title=clean(book.get("title"));slug=clean(book.get("slug"))
    root_url=f"{BOOKS_BASE}/{slug}/"
    if canonical.rstrip("/")==root_url.rstrip("/"):
        hub=profile.get("cluster") or "other-books";hub_label=profile.get("cluster_label") or "Books by Topic"
        items=[{"@type":"ListItem","position":1,"name":"Books","item":f"{BOOKS_BASE}/"},{"@type":"ListItem","position":2,"name":hub_label,"item":f"{BOOKS_BASE}/topics/{hub}/"},{"@type":"ListItem","position":3,"name":title,"item":canonical}]
    else:
        labels={"tr":"Türkçe katalog","ru":"Русский каталог","de":"Deutscher Katalog","es":"Catálogo en español","fr":"Catalogue français","pt-BR":"Catálogo em português"}
        path_code=LOCALE_PATHS.get(locale,locale.lower())
        items=[{"@type":"ListItem","position":1,"name":"Books","item":f"{BOOKS_BASE}/"},{"@type":"ListItem","position":2,"name":labels.get(locale,"Books"),"item":f"{BOOKS_BASE}/{path_code}/"},{"@type":"ListItem","position":3,"name":title,"item":canonical}]
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items}

def semantic_head_block(book,profile,locale):
    local=(profile.get("localized") or {}).get(locale,(profile.get("localized") or {}).get("en",{}))
    tags=unique(list(profile.get("entities") or [])+list(local.get("secondary_queries") or []))[:10]
    lines=[SEO_START,f'<meta property="book:author" content="{AUTHOR}">'];published=clean(book.get("published_date"))
    if published:lines.append(f'<meta property="book:release_date" content="{esc(published)}">')
    for tag in tags:lines.append(f'<meta property="book:tag" content="{esc(tag)}">')
    lines.append(SEO_END);return "\n".join(lines)

def related_block(book,profile,locale,books_by_slug):
    heading,note,hub_cta=RELATED_COPY.get(locale,RELATED_COPY["en"]);related=[]
    for slug in profile.get("related_slugs") or []:
        target=books_by_slug.get(slug)
        if not target:continue
        related.append(f'<li><a href="{esc(url_for_slug(slug,locale))}">{esc(target.get("title") or slug)}</a></li>')
    if not related:return ""
    hub=profile.get("cluster") or "other-books";hub_url=f"{BOOKS_BASE}/topics/{hub}/"
    return f'\n{RELATED_START}\n<section class="section semantic-related-books" aria-label="{esc(heading)}"><h2>{esc(heading)}</h2><p>{esc(note)}</p><ul>{"".join(related)}</ul><p><a href="{esc(hub_url)}">{esc(hub_cta)} →</a></p></section>\n{RELATED_END}\n'

def patch_page(path,book,profile,books_by_slug):
    text=path.read_text(encoding="utf-8");original=text;locale=page_locale(text);canonical=canonical_from(text,f"{BOOKS_BASE}/{book['slug']}/")
    text=re.sub(r'\s*<meta\b[^>]*name=["\']keywords["\'][^>]*>\s*',"\n",text,flags=re.I)
    text=re.sub(re.escape(SEO_START)+r".*?"+re.escape(SEO_END)+r"\s*","",text,flags=re.S)
    if "</head>" in text:text=text.replace("</head>",semantic_head_block(book,profile,locale)+"\n</head>",1)
    text=enrich_jsonld(text,book,profile,locale)
    if not has_schema_type(text,"Book") and "</head>" in text:
        book_block='<script type="application/ld+json">'+json.dumps(standalone_book_schema(book,profile,locale,canonical),ensure_ascii=False,separators=(",",":"))+'</script>'
        text=text.replace("</head>",book_block+"\n</head>",1)
    if not has_breadcrumb_schema(text) and "</head>" in text:
        block='<script type="application/ld+json">'+json.dumps(breadcrumb_schema(book,profile,locale,canonical),ensure_ascii=False,separators=(",",":"))+'</script>'
        text=text.replace("</head>",block+"\n</head>",1)
    text=re.sub(r'<section class="section">\s*<h2>Related books</h2>.*?</section>\s*',"",text,flags=re.S|re.I)
    text=re.sub(re.escape(RELATED_START)+r".*?"+re.escape(RELATED_END)+r"\s*","",text,flags=re.S)
    block=related_block(book,profile,locale,books_by_slug)
    if block and "</main>" in text:text=text.replace("</main>",block+"</main>",1)
    if text!=original:path.write_text(text,encoding="utf-8");return True
    return False

def hub_html(cluster,books,profiles):
    slug=cluster["slug"];label=cluster["label"];canonical=f"{BOOKS_BASE}/topics/{slug}/";rows=[];itemlist=[]
    for idx,book in enumerate(sorted(books,key=lambda b:clean(b.get("title")).casefold()),start=1):
        title=clean(book.get("title"));bslug=clean(book.get("slug"));profile=profiles.get(bslug,{});cover=clean(book.get("cover_url"));desc=clean(book.get("seo_description")) or clean(book.get("subtitle"))
        img=f'<img src="{esc(cover)}" alt="Book cover of {esc(title)} by Faramarz Kowsari" loading="lazy" decoding="async">' if cover else ""
        entities=", ".join((profile.get("entities") or [])[:4])
        rows.append(f'<article class="hub-card"><a href="../../{esc(bslug)}/">{img}<h2>{esc(title)}</h2></a>'+ (f'<p>{esc(desc)}</p>' if desc else "") + (f'<p class="small">{esc(entities)}</p>' if entities else "") + '</article>')
        itemlist.append({"@type":"ListItem","position":idx,"name":title,"url":f"{BOOKS_BASE}/{bslug}/"})
    queries="".join(f"<li>{esc(x)}</li>" for x in cluster["query_examples"])
    schema={"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":canonical+"#collection","url":canonical,"name":label,"description":cluster["description"],"inLanguage":"en","author":{"@type":"Person","name":AUTHOR,"url":f"{BOOKS_BASE}/author/"},"mainEntity":{"@type":"ItemList","numberOfItems":len(itemlist),"itemListElement":itemlist}},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Books","item":f"{BOOKS_BASE}/"},{"@type":"ListItem","position":2,"name":"Books by Topic","item":f"{BOOKS_BASE}/topics/"},{"@type":"ListItem","position":3,"name":label,"item":canonical}]}]}
    css=":root{color-scheme:light dark;--bg:#f6f8fc;--surface:#fff;--text:#172033;--muted:#5e6877;--line:#dfe5ef;--accent:#245cc7}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}main{width:min(1120px,calc(100% - 32px));margin:auto;padding:30px 0 70px}a{color:var(--accent);text-underline-offset:3px}.hero,.search-intent{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:24px;margin-bottom:22px}h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.08;margin:.2em 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}.hub-card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px}.hub-card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:10px}.hub-card h2{font-size:1.15rem;line-height:1.25}.small{color:var(--muted);font-size:.92rem}.crumbs{margin-bottom:18px}@media(prefers-color-scheme:dark){:root{--bg:#101722;--surface:#182233;--text:#eef3fb;--muted:#b7c2d1;--line:#334155;--accent:#a9c2ff}}"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><title>{esc(label)} Books | Faramarz Kowsari</title><meta name="description" content="{esc(cluster["description"][:290])}"><link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="website"><meta property="og:title" content="{esc(label)} Books | Faramarz Kowsari"><meta property="og:description" content="{esc(cluster["description"][:290])}"><meta property="og:url" content="{esc(canonical)}"><style>{css}</style><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(",",":"))}</script></head><body><main><nav class="crumbs"><a href="../../">Books</a> › <a href="../">Books by Topic</a> › {esc(label)}</nav><section class="hero"><h1>{esc(label)}</h1><p>{esc(cluster["description"])}</p><p>This hub is generated from the controlled subject metadata of the public books library. It connects closely related titles with descriptive internal links and a stable crawlable URL.</p></section><section class="search-intent"><h2>Common search themes</h2><ul>{queries}</ul></section><section class="grid">{''.join(rows)}</section></main></body></html>'''

def build_hubs(books,profiles):
    TOPICS.mkdir(parents=True,exist_ok=True);grouped={};by_cluster={c["slug"]:c for c in CLUSTERS}
    fallback={"slug":"other-books","label":"Other Books","description":"Additional books in the Faramarz Kowsari library.","query_examples":["Faramarz Kowsari books"],"terms":()};by_cluster[fallback["slug"]]=fallback
    for book in books:
        slug=clean(book.get("slug"));cluster_slug=(profiles.get(slug) or {}).get("cluster","other-books");grouped.setdefault(cluster_slug,[]).append(book)
    built=[]
    for cluster_slug,items in sorted(grouped.items()):
        if not items:continue
        cluster=by_cluster.get(cluster_slug,fallback);out=TOPICS/cluster_slug/"index.html";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(hub_html(cluster,items,profiles),encoding="utf-8");built.append((cluster,len(items)))
    return built

def patch_topics_index(hubs):
    path=TOPICS/"index.html"
    if not path.exists():return False
    text=path.read_text(encoding="utf-8");original=text;text=re.sub(re.escape(HUBS_START)+r".*?"+re.escape(HUBS_END)+r"\s*","",text,flags=re.S)
    cards="".join(f'<article class="topic-book-card"><div class="topic-book-body"><h3><a href="./{esc(cluster["slug"])}/">{esc(cluster["label"])}</a></h3><div class="topic-badges"><span class="topic-badge">{count} books</span></div><p>{esc(cluster["description"][:220])}</p></div></article>' for cluster,count in hubs)
    block=f'\n{HUBS_START}\n<section class="topic-group semantic-topic-hubs" id="semantic-topic-hubs"><div class="topic-group-header"><h2>Focused Topic Hubs</h2><span class="topic-count">{len(hubs)} hubs</span></div><p>Focused subject hubs connect closely related titles with descriptive internal links and stable crawlable URLs.</p><div class="topic-books-grid">{cards}</div></section>\n{HUBS_END}\n'
    marker='<div id="topic-groups">'
    if marker in text:text=text.replace(marker,block+marker,1)
    elif "</main>" in text:text=text.replace("</main>",block+"</main>",1)
    if text!=original:path.write_text(text,encoding="utf-8");return True
    return False

def apply():
    books=load_json(DATA,[]);profiles=load_json(SEO_DATA,{})
    if not isinstance(books,list) or not isinstance(profiles,dict):raise SystemExit("Run semantic_seo_books.py prepare before apply")
    active=[b for b in books if isinstance(b,dict) and clean(b.get("slug")) and b.get("status","active")=="active" and (BOOKS/clean(b.get("slug"))/"index.html").exists()]
    books_by_slug={clean(b.get("slug")):b for b in active};hubs=build_hubs(active,profiles);patch_topics_index(hubs);changed=0;pages=0
    for slug,book in books_by_slug.items():
        profile=profiles.get(slug)
        if not profile:continue
        candidates=[BOOKS/slug/"index.html"]+[BOOKS/slug/p/"index.html" for p in ("ru","tr","de","es","fr","pt-br")]
        for path in candidates:
            if not path.exists():continue
            pages+=1;changed+=int(patch_page(path,book,profile,books_by_slug))
    print(f"Semantic SEO apply: {changed}/{pages} book landing pages enriched; {len(hubs)} topic hubs built.")

def main():
    parser=argparse.ArgumentParser();parser.add_argument("phase",choices=("prepare","apply"));args=parser.parse_args()
    prepare() if args.phase=="prepare" else apply()

if __name__=="__main__":main()
