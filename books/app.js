async function loadBooks(){
  const [booksResponse,completedResponse]=await Promise.all([
    fetch('./books.json'),
    fetch('./completed.json').catch(()=>null)
  ]);
  const completed=completedResponse&&completedResponse.ok?await completedResponse.json():{};
  const all=(await booksResponse.json()).filter(b=>b.status==='active').map(b=>{
    const overlay=completed[b.slug]||{};
    return {...b,...overlay,source_reviewed:Boolean(completed[b.slug])};
  });

  const q=document.getElementById('q');
  const grid=document.getElementById('grid');
  const count=document.getElementById('count');
  const completedGrid=document.getElementById('completed-grid');
  const featuredCount=document.getElementById('completed-count');
  const sourceReviewed=all.filter(b=>b.source_reviewed);

  function card(b,featured=false){
    const details=[b.source_reviewed?'Source-reviewed':'',b.language,b.category]
      .filter(Boolean).map(escapeHtml).join(' · ') || 'Details being enriched';
    return `<article class="card">
      <img class="cover" src="${b.cover_url}" alt="${escapeHtml(b.title)} book cover" loading="lazy" decoding="async">
      <div class="card-body">
        <h2>${escapeHtml(b.title)}</h2>
        <div class="meta">${details}</div>
        <a class="btn" href="./${encodeURIComponent(b.slug)}/">${featured?'View source-reviewed page':'View book'}</a>
      </div>
    </article>`;
  }

  if(featuredCount){
    featuredCount.textContent=`${sourceReviewed.length} source-reviewed pages are ready for search indexing.`;
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
  document.getElementById('grid').innerHTML='<p>Could not load the library data.</p>';
  console.error(err);
});
