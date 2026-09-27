#!/usr/bin/env python3
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=ROOT/"index.html"
s=p.read_text(encoding="utf-8")
old=s
if 'rel="sitemap"' not in s:
    s=s.replace('<link rel="canonical" href="https://faramarzkowsari.github.io/">','<link rel="canonical" href="https://faramarzkowsari.github.io/">\n  <link rel="sitemap" type="application/xml" href="https://faramarzkowsari.github.io/sitemap.xml">',1)
if 'https://faramarzkowsari.github.io/books/#collection' not in s:
    block='''\n  <script type="application/ld+json">\n  {"@context":"https://schema.org","@type":"CollectionPage","@id":"https://faramarzkowsari.github.io/books/#collection","name":"Books by Faramarz Kowsari","url":"https://faramarzkowsari.github.io/books/","description":"Official multilingual book library of Faramarz Kowsari with permanent landing pages and Google Books links.","author":{"@id":"https://faramarzkowsari.github.io/#person"}}\n  </script>\n'''
    s=s.replace('</head>',block+'</head>',1)
if 'href="/books/"' not in s:
    target='<div class="actions centered">\n          <a class="button primary" href="https://play.google.com/store/search?q=Faramarz%20Kowsari&c=books">Google Play Books</a>'
    repl='<div class="actions centered">\n          <a class="button primary" href="/books/">Browse Official Book Library</a>\n          <a class="button secondary" href="https://play.google.com/store/search?q=Faramarz%20Kowsari&c=books">Google Play Books</a>'
    s=s.replace(target,repl,1)
if '<a href="/books/">Books</a>' not in s:
    s=s.replace('<div class="footer-links"><a href="sitemap.xml">Sitemap</a>','<div class="footer-links"><a href="/books/">Books</a><a href="sitemap.xml">Sitemap</a>',1)
if s!=old:p.write_text(s,encoding="utf-8");print("SEO root: internal Books links and collection schema added.")
else:print("SEO root: already optimized.")