# Faramarz Kowsari — Official Website & Books Library

[![DOI](https://zenodo.org/badge/1305358280.svg)](https://doi.org/10.5281/zenodo.23046366)

This repository powers the official website and multilingual book catalog of **Faramarz Kowsari**, an Istanbul-based author, researcher, software engineer, and AI-focused educator.

The project publishes permanent, crawlable pages for books across artificial intelligence, trading, data science, business, personal finance, psychology, mindfulness, personal development, language learning, and related subjects.

## Live Website

- Official website: https://faramarzkowsari.github.io/
- Books library: https://faramarzkowsari.github.io/books/
- Browse books by topic: https://faramarzkowsari.github.io/books/topics/
- Author profile: https://faramarzkowsari.github.io/books/author/
- Google Books catalog: https://play.google.com/store/search?q=Faramarz%20Kowsari&c=books

## DOI and Citation

This repository is archived on Zenodo and has persistent DOI identifiers.

- **Concept DOI — all versions:** https://doi.org/10.5281/zenodo.23046366
- **Version DOI — v1.0.0:** https://doi.org/10.5281/zenodo.23046367
- **GitHub release — v1.0.0:** https://github.com/FaramarzKowsari/FaramarzKowsari.github.io/releases/tag/v1.0.0
- **Author ORCID:** https://orcid.org/0000-0003-1692-0453

For reproducible citation of the archived `v1.0.0` release, use the version DOI. For references to the evolving project across versions, use the Concept DOI.

Machine-readable citation metadata is provided in [`CITATION.cff`](./CITATION.cff).

## About the Books Library

The `/books/` section is designed as a structured public catalog rather than a simple list of titles. Each published book can have its own permanent page with metadata, cover art, language and subject information, Google Books links, preview links when available, author references, accessibility improvements, and search-engine-friendly structured data.

The catalog is multilingual and currently includes titles in English, Turkish, Spanish, French, German, Persian, and other editions as they are added.

Major subject areas include:

- Artificial Intelligence and AI Engineering
- Prompt Engineering and AI Tools
- Trading, Smart Money Concepts, Market Structure, and Technical Analysis
- Data Science, Machine Learning, and SQL
- Business, Entrepreneurship, and Personal Finance
- Psychology, Self-Awareness, and Personal Development
- Mindfulness, Inner Growth, and Creative Thought
- Language Learning and Educational Resources

## Repository Structure

- `index.html` — main author website homepage
- `books/index.html` — public books catalog
- `books/topics/` — topic-based book navigation
- `books/author/` — author profile page
- `books/*/index.html` — dedicated pages for individual books
- `books/books.json` — structured catalog data
- `books/completed.json` — publication/completion state used by the build system
- `books/source_reviews/` — source-review material for book pages
- `scripts/` — build, SEO, accessibility, navigation, catalog, and publishing scripts
- `.github/workflows/` — automated GitHub Actions workflows
- `robots.txt` — crawler permissions
- `sitemap.xml` and book sitemaps — indexable URL discovery
- `404.html` — custom error page
- `.nojekyll` — direct static-file serving through GitHub Pages

## Automated Publishing Pipeline

The repository uses GitHub Actions to rebuild and publish the book catalog when relevant source data or scripts change. The automated process includes catalog merging, page generation, SEO enhancement, public-page cleanup, Google Books preview integration, author-link insertion, topic-index generation, and WCAG-oriented accessibility improvements.

This means the public book pages are generated consistently from structured data instead of being maintained as disconnected manual HTML pages.

## SEO and Discoverability

The site is built to support search-engine discovery through:

- Permanent canonical URLs
- Crawlable static HTML pages
- XML sitemaps
- Schema.org structured data
- Open Graph and Twitter metadata
- Language-aware metadata and alternate-language links where available
- Internal navigation between the books catalog, topic index, author profile, and individual titles
- Direct Google Books destinations

## Accessibility

The books catalog includes accessibility-oriented improvements such as semantic navigation, descriptive image alternative text, accessible link labels, keyboard skip navigation, search labeling, status announcements, and other WCAG 2.2 AA-oriented enhancements.

## Author

**Faramarz Kowsari** is an author and researcher based in Istanbul. His work focuses on the intersection of technology, education, artificial intelligence, modern trading, personal growth, and practical digital learning.

Official profiles and publications are linked from the author page:

https://faramarzkowsari.github.io/books/author/

## Purpose of This Repository

The goal of this repository is to maintain a durable, searchable, multilingual public home for Faramarz Kowsari's published work while connecting readers to official book pages and Google Books destinations.

The repository also serves as the technical foundation for an expanding digital publishing system in which new titles can be added to structured catalog data and propagated automatically into the public website.

## Google Search Console

Use this URL as the main URL-prefix property:

https://faramarzkowsari.github.io/

For the books catalog, the principal public collection URL is:

https://faramarzkowsari.github.io/books/

---

**Official Books Library:** https://faramarzkowsari.github.io/books/  
**Browse by Topic:** https://faramarzkowsari.github.io/books/topics/  
**Author Profile:** https://faramarzkowsari.github.io/books/author/  
**Zenodo Concept DOI:** https://doi.org/10.5281/zenodo.23046366
