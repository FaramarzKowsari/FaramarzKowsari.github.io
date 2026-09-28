#!/usr/bin/env python3
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"

SECTION_RE = re.compile(r'\n?<section class="section">.*?</section>\n?', re.S | re.I)
TAG_RE = re.compile(r'<[^>]+>')

A1_ABOUT = '''<section class="section">
<h2>A complete visual A1 Turkish course in one volume</h2>
<p><strong>Turkish A1 Visual Grammar</strong> brings Books 1-5 plus the A1 Booster together in a 307-page illustrated course designed to help beginners move from first words and basic sentence patterns toward confident everyday Turkish. Grammar is presented visually, with clear examples, recurring characters, compact explanations and cumulative practice so learners can see how Turkish words are built and how suffixes change meaning.</p>
<p>The collection develops the Turkish alphabet and vowel harmony, nominal sentences, possession, <em>var / yok</em>, common verbs, present continuous, case endings, movement and time expressions, daily routines, past and future forms, cumulative quests and an expanded grammar map. It is designed as a single reference learners can return to while building a strong, practical A1 foundation.</p>
</section>'''

A2_ABOUT = '''<section class="section">
<h2>A complete visual A2 Turkish course in one collection</h2>
<p><strong>Turkish A2 Visual Grammar</strong> brings Books 6-11 together in a 306-page illustrated course for learners ready to move beyond beginner Turkish. The collection develops deeper noun structures, definite objects, compound nouns, possessive and case chains, comparisons, ability, necessity, obligation, advice, habits and the aorist, then continues into richer sentence building, clauses, reasons and conditions, verbals, reported speech and final A2 consolidation.</p>
<p>The teaching style is visual, cumulative and practical. Turkish forms are broken into roots, suffixes, buffer consonants and personal endings, then rebuilt through short examples, dialogues, mini stories, review charts and challenge-based practice. It is especially useful for self-study learners who want grammar to become easier to recognize, remember and use in real communication.</p>
</section>'''

PROCESS_MARKERS = (
    'source review status',
    'source-reviewed for this page',
    'source examined so far',
    'source material reviewed so far',
    'still required for full source-level analysis',
    'when their source pages are supplied',
    'former individual google books listings',
    'google books publication structure',
    'reviewed: 150 pages',
    'partial source review',
    'can be added here later without changing this page url',
)


def plain_text(block):
    return re.sub(r'\s+', ' ', TAG_RE.sub(' ', block)).strip().lower()


def clean_section(match):
    block = match.group(0)
    text = plain_text(block)
    if any(marker in text for marker in PROCESS_MARKERS):
        return '\n'
    return block


def clean_a1(html):
    replacements = {
        '<title>Turkish A1 Visual Grammar | Complete Combined A1 Turkish Course</title>':
            '<title>Turkish A1 Visual Grammar | Complete 6-Book A1 Turkish Course</title>',
        'Turkish A1 Visual Grammar is the single combined A1 Google Books edition containing the original Books 1-5 plus the A1 Booster in one 307-page illustrated beginner Turkish course.':
            'Turkish A1 Visual Grammar is a 307-page illustrated beginner course combining Books 1-5 and the A1 Booster to teach grammar, vocabulary, sentence building, tenses, cases and everyday Turkish.',
        'One combined A1 edition: the original Books 1-5 plus the A1 Booster in a single 307-page Google Books product.':
            'A complete 307-page visual A1 Turkish course combining Books 1-5 and the A1 Booster for grammar, vocabulary, sentence building and everyday Turkish.',
        'The complete combined A1 Turkish grammar edition: original Books 1-5 + A1 Booster in one illustrated course.':
            'A complete illustrated A1 Turkish grammar course with Books 1-5 plus the A1 Booster in one 307-page collection.',
        'The single combined A1 Google Books edition containing the original Books 1-5 plus the A1 Booster in one 307-page illustrated beginner Turkish course.':
            'A 307-page illustrated A1 Turkish course covering grammar, vocabulary, sentence building, tenses, cases and everyday Turkish through Books 1-5 plus the A1 Booster.',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    html = re.sub(
        r'<section class="section">\s*<h2>About this combined A1 edition</h2>.*?</section>',
        A1_ABOUT,
        html,
        flags=re.S | re.I,
    )
    html = re.sub(r'Original Book ([1-5]) material —', r'Book \1 —', html)
    html = html.replace('Read / Buy the Combined A1 Edition on Google Books', 'Read / Buy the Complete A1 Collection on Google Books')
    return html


def clean_a2(html):
    replacements = {
        '<title>Turkish A2 Visual Grammar | Complete Combined A2 Turkish Course</title>':
            '<title>Turkish A2 Visual Grammar | Complete 6-Book A2 Turkish Course</title>',
        'Turkish A2 Visual Grammar is the single combined A2 Google Books edition containing the original Books 6-11 in one illustrated intermediate Turkish course.':
            'Turkish A2 Visual Grammar is a 306-page illustrated A2 Turkish course combining Books 6-11 for grammar, sentence building, everyday communication and confident intermediate-level progress.',
        'One combined A2 edition: the original Books 6-11 in a single illustrated Google Books product for intermediate Turkish grammar and communication.':
            'A complete 306-page visual A2 Turkish course combining Books 6-11 for intermediate grammar, sentence building, communication and real-life Turkish.',
        'The complete combined A2 Turkish grammar edition: original Books 6-11 in one illustrated Google Books course.':
            'A complete illustrated A2 Turkish grammar course bringing Books 6-11 together in one 306-page collection.',
        'The single combined A2 Google Books edition containing the original Books 6-11 in one illustrated intermediate Turkish course.':
            'A 306-page illustrated A2 Turkish course covering intermediate grammar, sentence building, communication, clauses, verbals and reported speech through Books 6-11.',
        'What learners practice in the reviewed portion':
            'What learners practice',
        'The Book 6 portion develops the noun system beyond beginner-level forms.':
            'Book 6 develops the noun system beyond beginner-level forms.',
        'The Book 7 portion organizes modal meanings into a practical progression.':
            'Book 7 organizes modal meanings into a practical progression.',
        'The Book 8 portion introduces the Turkish <strong>aorist / geniş zaman</strong> as a system for habits, routines, repeated actions and general truths.':
            'Book 8 introduces the Turkish <strong>aorist / geniş zaman</strong> as a system for habits, routines, repeated actions and general truths.',
        'Mini stories, family habits, café routines, review charts and a final boss-style review consolidate the material before it continues into the original Book 9 section of the combined A2 edition.':
            'Mini stories, family habits, café routines, review charts and a final boss-style review consolidate the material and prepare learners for the later A2 units.',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    html = re.sub(
        r'<section class="section">\s*<h2>About this combined A2 edition</h2>.*?</section>',
        A2_ABOUT,
        html,
        flags=re.S | re.I,
    )
    html = re.sub(r'Original Book (\d+) material —', r'Book \1 —', html)
    html = html.replace('Read / Buy the Combined A2 Edition on Google Books', 'Read / Buy the Complete A2 Collection on Google Books')
    return html


def clean_catalog(html):
    replacements = {
        'Browse source-reviewed books by Faramarz Kowsari': 'Browse books by Faramarz Kowsari',
        'A multilingual library of source-reviewed book pages with direct Google Books links.': 'A multilingual library of books by Faramarz Kowsari with direct Google Books links.',
        'AI, trading, business, technology and personal-growth books with permanent source-reviewed pages.': 'AI, trading, business, technology and personal-growth books with dedicated pages and direct Google Books links.',
        'Multilingual source-reviewed books by Faramarz Kowsari with direct Google Books links.': 'Multilingual books by Faramarz Kowsari with direct Google Books links.',
        'Every source-reviewed title below has a permanent crawlable page and a direct Google Books destination.': 'Explore the titles below by subject, language and interest, with dedicated book pages and direct Google Books destinations.',
        'Source-reviewed book pages': 'Explore the book collection',
        'crawlable book pages.': 'books.',
        'crawlable book page': 'book',
        'Source-reviewed book': 'Book',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    return html


def clean_file(path):
    html = path.read_text(encoding='utf-8')
    original = html

    if path.parent.name == 'turkish-a1-visual-grammar':
        html = clean_a1(html)
    elif path.parent.name == 'turkish-a2-visual-grammar':
        html = clean_a2(html)

    html = html.replace(
        'More source-reviewed books will be linked here as the library expands.',
        '<a href="../">Browse more books by Faramarz Kowsari</a>.'
    )
    html = re.sub(r'\s*<p class="small">\s*Google Books ID:.*?</p>', '', html, flags=re.S | re.I)
    html = SECTION_RE.sub(clean_section, html)

    if path == BOOKS / 'index.html':
        html = clean_catalog(html)

    html = html.replace('source-reviewed', 'detailed')
    html = html.replace('Source-reviewed', 'Detailed')
    html = re.sub(r'\bsource review\b', 'book information', html, flags=re.I)
    html = re.sub(r'\n{3,}', '\n\n', html)

    if html != original:
        path.write_text(html, encoding='utf-8')
        return True
    return False


changed = 0
for path in sorted(BOOKS.glob('*/index.html')):
    changed += int(clean_file(path))

catalog = BOOKS / 'index.html'
if catalog.exists():
    changed += int(clean_file(catalog))

print(f'Public-facing cleanup updated {changed} book/catalog pages.')
