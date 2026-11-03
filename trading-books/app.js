(() => {
  const search = document.getElementById('book-search');
  const cards = [...document.querySelectorAll('.book-card')];
  const sections = [...document.querySelectorAll('.book-section')];
  const filters = [...document.querySelectorAll('.category-filter')];
  const count = document.getElementById('visible-count');
  const noResults = document.getElementById('no-results');
  let activeFilter = 'all';

  function normalize(value) {
    return (value || '').toLowerCase().normalize('NFKD');
  }

  function applyFilters() {
    const q = normalize(search?.value.trim());
    let visible = 0;
    cards.forEach(card => {
      const categoryOk = activeFilter === 'all' || card.dataset.category === activeFilter;
      const haystack = normalize(card.dataset.search);
      const searchOk = !q || haystack.includes(q);
      const show = categoryOk && searchOk;
      card.hidden = !show;
      if (show) visible += 1;
    });

    sections.forEach(section => {
      section.hidden = !section.querySelector('.book-card:not([hidden])');
    });

    if (count) count.textContent = visible;
    if (noResults) noResults.hidden = visible !== 0;
  }

  filters.forEach(button => {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.filter || 'all';
      filters.forEach(b => b.classList.toggle('is-active', b === button));
      applyFilters();
      if (activeFilter !== 'all') {
        document.getElementById(activeFilter)?.scrollIntoView({behavior:'smooth', block:'start'});
      }
    });
  });

  search?.addEventListener('input', applyFilters);

  const copyButtons = [
    document.getElementById('copy-showcase-link'),
    document.getElementById('copy-showcase-link-bottom')
  ].filter(Boolean);

  copyButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText('https://faramarzkowsari.github.io/trading-books/');
        button.textContent = 'Link copied';
      } catch {
        button.textContent = 'Copy failed';
      }
      window.setTimeout(() => button.textContent = original, 1600);
    });
  });

  document.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (typeof window.gtag === 'function' && href.includes('play.google.com')) {
      window.gtag('event', 'google_books_click', {
        link_url: href,
        link_text: (link.textContent || '').trim()
      });
    }
    if (typeof window.gtag === 'function' && href.includes('medium.com')) {
      window.gtag('event', 'medium_article_click', {
        link_url: href,
        link_text: (link.textContent || '').trim()
      });
    }
  });

  applyFilters();
})();