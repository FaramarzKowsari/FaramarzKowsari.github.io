# Books Library v1

Initial scalable library generated from 138 unique Google Books links.

## What is included
- Searchable `/books/` index
- 138 unique book URLs
- External Google Books cover images (no local cover storage)
- Per-book Google Books purchase/view link
- `books.json` as the source of truth
- Fields reserved for language, category, translation groups, summaries, YouTube, podcast, slides, DOI/Crossref, and visibility
- `active / hidden / removed` architecture
- Pending pages use `noindex,follow` until their PDF-derived editorial content is complete

## Safe installation
Copy the `books` and `scripts` folders into the root of the `FaramarzKowsari.github.io` repository while the current branch is `books-library-v1`.
Then commit and push from GitHub Desktop. Do not merge into `main` yet.

## PDF workflow
PDF filenames do not have to be renamed. Matching can be done from title/author/language inside the PDF.
Using the Google Books ID as the filename is still the safest convention when convenient.
