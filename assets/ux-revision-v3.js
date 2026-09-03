(function(){
  const PROG_KEY='ldm-progress-v4';
  function saveP(){localStorage.setItem(PROG_KEY,JSON.stringify(progress));}
  function st(c){return c.mastered?'Learned':((c.reps||0)>0?'Learning':'New')}
  function esc2(s){return esc(s)}
  function getStatusClass(x){return x==='Learned'?'status-learned':x==='Learning'?'status-learning':'status-new'}
  function statusLower(x){return x==='Learned'?'learned':x==='Learning'?'learning':'new'}
  const style=document.createElement('style');
  style.textContent=`
    .status-badge{display:inline-block;padding:4px 9px;border-radius:999px;border:1px solid var(--line);font-size:11px;font-weight:700;white-space:nowrap}
    .status-learning{background:#f3e1c1}.status-learned{background:#dcefe0;border-color:#7aae85}.status-new{background:#fffdf8}
    .words-edit-input{width:100%;min-width:115px;border:1px solid var(--line);background:#fffdf8;border-radius:5px;padding:9px 8px;font:13px inherit;color:var(--ink)}
    .words-edit-select{width:100%;border:1px solid var(--line);background:#fffdf8;border-radius:999px;padding:8px 7px;font:600 13px inherit;color:var(--ink)}
    .words-show{min-width:145px;line-height:1.35}.words-actions{display:flex;gap:5px;align-items:center}.iconbtn{width:42px;height:42px;border:1px solid var(--bg);border-radius:6px;background:transparent;color:var(--bg);cursor:pointer;font-size:18px}.iconbtn.delete{font-size:22px}
    .flash-song{font-size:13px;opacity:.9;margin:10px 0 2px}.flash-meaning{font:italic 27px Georgia,serif;margin:7px 0 13px}.flash-line{font-size:15px;line-height:1.5;max-width:500px}.flash-line-en{font-size:13px;opacity:.85;line-height:1.45;max-width:500px;margin-top:5px}
    .study-progress{font-size:12px;color:var(--soft);text-align:center;margin:8px 0}
    #wordsView table{min-width:1180px}
  `;
  document.head.appendChild(style);
  function wordMatches(c,q,field){
    if(!q)return true;
    const w=String(c.word||'').toLowerCase(), l=String(c.line||'').toLowerCase(), t=String(c.translation||'').toLowerCase();
    if(field==='word')return w.includes(q); if(field==='lyrics')return l.includes(q); if(field==='translation')return t.includes(q);
    return w.includes(q)||l.includes(q)||t.includes(q);
  }
  function renderWordsV3(){
    const body=$('wordBody'); if(!body)return;
    const q=($('wordsSearch')?.value||'').trim().toLowerCase(), field=$('wordsSearchField')?.value||'all', lv=$('wordsLevel')?.value||'';
    let arr=(cards||[]).filter(c=>(!lv||c.level===lv)&&wordMatches(c,q,field));
    const total=arr.length, per=50, pages=Math.max(1,Math.ceil(total/per)); pageNo=Math.min(Math.max(1,pageNo||1),pages);
    arr=arr.slice((pageNo-1)*per,pageNo*per);
    body.innerHTML=arr.map(c=>{
      const s=st(c), id=esc2(c.id);
      return `<tr>
        <td><input class="words-edit-input" data-f="word" data-id="${id}" value="${esc2(c.word||'')}"></td>
        <td><select class="words-edit-select" data-f="level" data-id="${id}">${LEVELS.map(x=>`<option ${x===c.level?'selected':''}>${x}</option>`).join('')}</select></td>
        <td><input class="words-edit-input" data-f="translation" data-id="${id}" value="${esc2(c.translation||'')}"></td>
        <td><input class="words-edit-input" data-f="line" data-id="${id}" value="${esc2(c.line||'')}"></td>
        <td class="words-show"><b>${esc2(c.show||c.musical||'')}</b><br><span class="tiny">${esc2(c.song||'')}</span></td>
        <td><span class="status-badge ${getStatusClass(s)}">${statusLower(s)}</span></td>
        <td><input type="checkbox" data-exclude="${id}" ${c.excluded?'checked':''}></td>
        <td><div class="words-actions"><button class="iconbtn" title="Edit" data-edit="${id}">✎</button><button class="iconbtn delete" title="Delete" data-delete="${id}">×</button></div></td>
      </tr>`;
    }).join('');
    $('page').textContent=`${pageNo} / ${pages} · ${total} words`;
    $('wordStatus').textContent=active?`${active.name} · ${total} matching words`:'Choose a Musical.';
    $('prev').disabled=pageNo<=1;$('next').disabled=pageNo>=pages;
  }
  function updateCardField(id,field,val){
    const p=progress[id]||{}; progress[id]={...p,[field]:val}; saveP();
    const c=cards.find(x=>x.id===id); if(c)c[field]=val;
  }
  function bindWords(){
    const body=$('wordBody'); if(!body)return;
    body.addEventListener('change',e=>{
      const el=e.target, id=el.dataset.id; if(!id)return;
      if(el.dataset.f==='level')updateCardField(id,'level',el.value);
      if(el.dataset.f==='word')updateCardField(id,'word',el.value);
      if(el.dataset.f==='translation')updateCardField(id,'translation',el.value);
      if(el.dataset.f==='line')updateCardField(id,'line',el.value);
      if(el.dataset.exclude)updateCardField(id,'excluded',el.checked);
      renderWordsV3();
    });
    body.addEventListener('click',e=>{
      const ed=e.target.closest('[data-edit]'), del=e.target.closest('[data-delete]');
      if(ed)openEdit(ed.dataset.edit);
      if(del){const id=del.dataset.delete;if(confirm('Delete this word from your saved browser data?')){delete progress[id];saveP();cards=cards.filter(x=>x.id!==id);renderWordsV3()}}
    });
    $('wordsSearch')?.addEventListener('input',()=>{pageNo=1;renderWordsV3()});
    $('wordsSearchField')?.addEventListener('change',()=>{pageNo=1;renderWordsV3()});
    $('wordsLevel')?.addEventListener('change',()=>{pageNo=1;renderWordsV3()});
    $('prev')?.addEventListener('click',()=>{pageNo--;renderWordsV3()}); $('next')?.addEventListener('click',()=>{pageNo++;renderWordsV3()});
  }
  let studyQueue=[], studyIndex=0, groupWords=[], studyFlipped=false, studyMixed=false;
  async function loadStudySelection(){
    const val=$('studyMusical')?.value; if(!val)return [];
    if(val==='__all__'){
      const out=[];
      for(const m of catalog.musicals||[]){const r=await fetch(m.cardsUrl+'?v='+Date.now(),{cache:'no-store'});const d=await r.json();out.push(...(d.cards||[]).map(merge))}
      return out;
    }
    return (await getMusical(val)).cards;
  }
  function filteredStudy(arr){
    const mode=$('studyMode')?.value||'due';
    let x=arr.filter(c=>!c.excluded&&levels.has(c.level));
    if(mode==='weak')x=x.filter(c=>!c.mastered&&(c.reps||0)>0);
    if(mode==='mastered')x=x.filter(c=>c.mastered);
    if(mode==='due')x=x.filter(c=>!c.mastered);
    return x;
  }
  function shuffle(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
  function renderStudyCard(){
    const c=groupWords[studyIndex]; if(!c){renderQuizV3();return}
    stop(); studyFlipped=false;
    const s=st(c);
    $('session').innerHTML=`<div class="studytools"><span class="muted">${studyMixed?'All musicals':'Musical'} · ${studyIndex+1} / ${groupWords.length}</span><button class="btn ghost" id="endStudyNow">End session</button></div>
      <div class="study-progress">Group of 10 · ${studyIndex+1} / ${groupWords.length}</div>
      <div class="card" id="studyCard"><div class="inner">
        <div class="face front"><div class="big">${esc2(c.word)}</div><div class="leveltag">${esc2(c.level)}</div><div class="muted" style="margin-top:12px">${s}</div><div class="tiny" style="margin-top:10px">Tap to flip</div></div>
        <div class="face back"><div class="big">${esc2(c.word)}</div><div class="flash-meaning">${esc2(c.translation||'—')}</div><div class="flash-song">${esc2(c.show||c.musical||'')} · ${esc2(c.song||'')}</div><div class="flash-line">${esc2(c.line||'')}</div><div class="flash-line-en">${esc2(c.lineTranslation||'')}</div></div>
      </div></div>
      <div class="actions"><button class="btn ghost" id="againBtn">↻ Again</button><button class="btn ghost" id="editStudyBtn">✎ Edit</button><button class="btn primary" id="knowBtn">Know it ✓</button></div>`;
    $('studyCard').onclick=e=>{if(e.target.closest('button'))return;studyFlipped=!studyFlipped;$('studyCard').classList.toggle('flipped',studyFlipped)};
    $('againBtn').onclick=()=>rateCard(false); $('knowBtn').onclick=()=>rateCard(true); $('editStudyBtn').onclick=()=>openEdit(c.id); $('endStudyNow').onclick=()=>{stop();$('session').classList.add('hidden');$('setup').classList.remove('hidden')};
    play(c);
  }
  function rateCard(known){
    const c=groupWords[studyIndex];if(!c)return;const p=progress[c.id]||{};
    progress[c.id]={...p,reps:(p.reps||0)+1,mastered:known};saveP();c.reps=(p.reps||0)+1;c.mastered=known;
    studyIndex++; if(studyIndex<groupWords.length)renderStudyCard(); else renderQuizV3();
  }
  function renderQuizV3(){
    const items=groupWords.slice(0,10); if(!items.length){finishStudy();return}
    let left=shuffle(items),right=shuffle(items),picked=null,matched=new Set();
    const sess=$('session');
    sess.innerHTML=`<div class="studytools"><span class="muted">Matching quiz · this ${items.length}-word group</span><button class="btn ghost" id="skipQuizV3">Skip quiz →</button></div><div class="quizgrid"><div class="quizcol" id="qLeft"></div><div class="quizcol" id="qRight"></div></div><div class="muted" style="text-align:center" id="quizMsg">Click a German word, then its English translation.</div>`;
    const render=()=>{
      $('qLeft').innerHTML=left.map(c=>`<button data-l="${esc2(c.id)}" ${matched.has(c.id)?'disabled':''} class="${matched.has(c.id)?'ok':''}">${esc2(c.word)}</button>`).join('');
      $('qRight').innerHTML=right.map(c=>`<button data-r="${esc2(c.id)}" ${matched.has(c.id)?'disabled':''} class="${matched.has(c.id)?'ok':''}">${esc2(c.translation||'')}</button>`).join('');
      if(matched.size===items.length){$('quizMsg').textContent='✓ Complete';const b=document.createElement('button');b.className='btn primary';b.textContent='Next group →';b.onclick=nextGroup;sess.appendChild(b)}
    };
    sess.onclick=e=>{const l=e.target.closest('[data-l]'),r=e.target.closest('[data-r]');if(l){picked=l.dataset.l;document.querySelectorAll('[data-l]').forEach(x=>x.classList.remove('sel'));l.classList.add('sel')} if(r&&picked){if(r.dataset.r===picked){matched.add(picked);picked=null;render()}else{$('quizMsg').textContent='Try again.';r.classList.add('bad');setTimeout(()=>r.classList.remove('bad'),450)}}};
    $('skipQuizV3').onclick=nextGroup;render();
  }
  function nextGroup(){
    const remaining=studyQueue.slice(groupWords.length); if(!remaining.length){finishStudy();return}
    studyQueue=remaining;groupWords=studyQueue.slice(0,10);studyIndex=0;renderStudyCard();
  }
  function finishStudy(){stop();$('session').innerHTML=`<div style="text-align:center;padding:35px 10px"><div class="big">Session complete ✓</div><p class="muted">Progress is saved automatically.</p><button class="btn primary" id="backSetup">Back to setup</button></div>`;$('backSetup').onclick=()=>{$('session').classList.add('hidden');$('setup').classList.remove('hidden')};}
  async function startStudyV3(){
    stop();
    try{
      const arr=filteredStudy(await loadStudySelection());
      studyQueue=shuffle(arr); studyMixed=$('studyMusical')?.value==='__all__';
      if(!studyQueue.length){alert('No words match this study selection.');return}
      groupWords=studyQueue.slice(0,10);studyIndex=0;$('setup').classList.add('hidden');$('session').classList.remove('hidden');renderStudyCard();
    }catch(e){alert('Could not load the study words: '+e.message)}
  }
  function addMixedOption(){
    const sel=$('studyMusical');if(!sel||sel.querySelector('option[value="__all__"]'))return;
    const o=document.createElement('option');o.value='__all__';o.textContent='All 4 musicals (mixed)';sel.insertBefore(o,sel.options[1]||null);
    const ord=$('studyOrder');if(ord){ord.value='random';ord.innerHTML='<option value="random">Random (default)</option><option value="level">Easiest first</option><option value="alpha">A–Z</option>'}
  }
  function init(){
    addMixedOption();bindWords();
    $('start')?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();startStudyV3()},true);
    $('shuffleSetup')?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();const ord=$('studyOrder');if(ord)ord.value='random'},true);
    const auto=$('autoPlay'); if(auto)auto.checked=true;
    document.querySelector('[data-view="words"]')?.addEventListener('click',()=>setTimeout(renderWordsV3,80));
    document.querySelector('[data-view="study"]')?.addEventListener('click',()=>setTimeout(addMixedOption,80));
    setTimeout(()=>{addMixedOption();renderWordsV3()},400);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
