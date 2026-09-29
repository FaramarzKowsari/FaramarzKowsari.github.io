async function loadBooks(){
  const [booksResponse,completedResponse,extraResponse]=await Promise.all([
    fetch('./books.json'),
    fetch('./completed.json').catch(()=>null),
    fetch('./source-reviewed-extra.json').catch(()=>null)
  ]);
  const completed=completedResponse&&completedResponse.ok?await completedResponse.json():{};
  const extra=extraResponse&&extraResponse.ok?await extraResponse.json():{};
  const reviewed={...completed,...extra};
  const coverOverrides={
    'turkish-a1-visual-grammar':'https://play.google.com/books/publisher/content/images/frontcover/5TjbEQAAQBAJ?fife=w480-h690',
    'turkish-a2-visual-grammar':'https://play.google.com/books/publisher/content/images/frontcover/F-TaEQAAQBAJ?fife=w480-h690'
  };
  const all=(await booksResponse.json()).filter(b=>b.status==='active').map(b=>{
    const overlay=reviewed[b.slug]||{};
    return {...b,...overlay,cover_url:coverOverrides[b.slug]||overlay.cover_url||b.cover_url,source_reviewed:Boolean(reviewed[b.slug])};
  });

  const q=document.getElementById('q');
  const grid=document.getElementById('grid');
  const count=document.getElementById('count');
  const completedGrid=document.getElementById('completed-grid');
  const featuredCount=document.getElementById('completed-count');
  const sourceReviewed=all.filter(b=>b.source_reviewed);

  function card(b,featured=false){
    const title=escapeHtml(b.title);
    const href=`./${encodeURIComponent(b.slug)}/`;
    const details=[b.language,b.category]
      .filter(Boolean).map(escapeHtml).join(' · ') || 'Book details';
    return `<article class="card">
      <a href="${href}" aria-label="Open the book page for ${title}"><img class="cover" src="${escapeHtml(b.cover_url)}" alt="Book cover of ${title} by Faramarz Kowsari" loading="lazy" decoding="async"></a>
      <div class="card-body">
        <h2><a href="${href}">${title}</a></h2>
        <div class="meta">${details}</div>
        <a class="btn" href="${href}" aria-label="View book: ${title}">${featured?'View book':'View book'}</a>
      </div>
    </article>`;
  }

  if(featuredCount){
    featuredCount.textContent=`${sourceReviewed.length} books`;
  }
  if(completedGrid){
    completedGrid.innerHTML=sourceReviewed.map(b=>card(b,true)).join('');
  }

  function render(){
    const term=(q.value||'').trim().toLowerCase();
    const rows=all.filter(b=>!term ||
      b.title.toLowerCase().includes(term) ||
      (b.category||'').toLowerCase().includes(term) ||
      (b.language||'').toLowerCase().includes(term));
    count.textContent=`${rows.length} book${rows.length===1?'':'s'}`;
    grid.innerHTML=rows.map(b=>card(b,false)).join('');
  }

  q.addEventListener('input',render);
  render();
}

function escapeHtml(s=''){
  return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

loadBooks().catch(err=>{
  document.getElementById('grid').innerHTML='<p role="status">Could not load the library data.</p>';
  console.error(err);
});
