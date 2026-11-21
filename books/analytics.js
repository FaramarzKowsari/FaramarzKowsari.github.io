// Collection only. Reports are served by the property's authenticated GA4 account.
(() => {
  if (location.hostname !== 'faramarzkowsari.github.io' || window.booksAnalyticsLoaded) return;
  window.booksAnalyticsLoaded = true;
  const measurementId = 'G-B8XLF16YDW';
  window.dataLayer = window.dataLayer || [];
  function track() { window.dataLayer.push(arguments); }
  track('js', new Date());
  track('config', measurementId, {
    allow_google_signals: false,
    allow_ad_personalization_signals: false
  });

  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
  document.head.appendChild(script);

  function recordLink(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    const link = event.target.closest?.('a[href]');
    if (!link || !['http:', 'https:'].includes(link.protocol)) return;
    const url = new URL(link.href);
    const googleBook = (url.hostname === 'play.google.com' &&
      (url.pathname.includes('/books/') || url.pathname.endsWith('/books'))) ||
      /^books\.google\.[a-z]{2,}(?:\.[a-z]{2})?$/.test(url.hostname);
    const details = {
      send_to: measurementId,
      link_domain: url.hostname,
      link_url: url.origin + url.pathname,
      link_id: link.id || undefined
    };
    if (googleBook && /^[\w-]+$/.test(url.searchParams.get('id') || '')) {
      details.link_url += '?id=' + url.searchParams.get('id');
    }
    track('event', 'book_link_click', details);
    if (googleBook) track('event', 'google_books_click', details);
  }
  document.addEventListener('click', recordLink, true);
  document.addEventListener('auxclick', recordLink, true);
})();
