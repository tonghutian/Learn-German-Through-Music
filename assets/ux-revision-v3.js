(function(){
  'use strict';
  const PREF_KEY='ldm-study-preferences-v1';
  const PROG_KEY='ldm-progress-v4';

  function loadOriginal(done){
    const s=document.createElement('script');
    s.src='assets/ux-revision-v3-original.js?v=9';
    s.onload=done;
    s.onerror=function(){console.error('Could not load original study UI')};
    document.head.appendChild(s);
  }
  function readPrefs(){try{return JSON.parse(localStorage.getItem(PREF_KEY)||'{}')||{}}catch(e){return {}}}
  function writePrefs(p){try{localStorage.setItem(PREF_KEY,JSON.stringify(p))}catch(e){}}

  function rememberStudyChoices(){
    const musical=document.getElementById('studyMusical'),mode=document.getElementById('studyMode'),order=document.getElementById('studyOrder');
    const activeLevels=[...document.querySelectorAll('#studyLevels .pill.active')].map(x=>x.dataset.level||x.textContent.trim()).filter(Boolean);
    const p=readPrefs();
    if(musical&&musical.value)p.musical=musical.value;
    if(mode&&mode.value)p.mode=mode.value;
    if(order&&order.value)p.order=order.value;
    if(activeLevels.length)p.levels=activeLevels;
    p.savedAt=Date.now();writePrefs(p);
  }

  function restoreStudyChoices(){
    const p=readPrefs(),musical=document.getElementById('studyMusical'),mode=document.getElementById('studyMode'),order=document.getElementById('studyOrder');
    if(musical&&p.musical&&[...musical.options].some(o=>o.value===p.musical))musical.value=p.musical;
    if(mode&&p.mode&&[...mode.options].some(o=>o.value===p.mode))mode.value=p.mode;
    if(order&&p.order&&[...order.options].some(o=>o.value===p.order))order.value=p.order;
    if(Array.isArray(p.levels)&&p.levels.length){
      const want=new Set(p.levels.map(String));
      document.querySelectorAll('#studyLevels .pill').forEach(b=>{
        const level=String(b.dataset.level||b.textContent.trim()),should=want.has(level),is=b.classList.contains('active');
        if(should!==is)b.click();
      });
    }
  }

  function installPreferenceSaving(){
    ['studyMusical','studyMode','studyOrder'].forEach(id=>document.getElementById(id)?.addEventListener('change',()=>setTimeout(rememberStudyChoices,0),true));
    document.addEventListener('click',function(e){
      if(e.target.closest?.('#studyLevels .pill'))setTimeout(rememberStudyChoices,30);
      if(e.target.closest?.('#start'))setTimeout(rememberStudyChoices,30);
      if(e.target.closest?.('[data-view="study"]'))setTimeout(restoreStudyChoices,120);
    },true);
    setTimeout(restoreStudyChoices,300);
    setTimeout(restoreStudyChoices,1000);
  }

  function installEditorRepair(){
    const form=document.getElementById('editForm'),modal=document.getElementById('editModal');
    if(!form||!modal)return;
    document.addEventListener('click',function(e){
      const button=e.target.closest?.('[data-edit],#editStudyBtn');if(!button)return;
      const directId=button.getAttribute('data-edit')||'';
      if(directId){modal.dataset.editId=directId;return;}
      setTimeout(function(){try{const id=eval('(typeof editingId!=="undefined"?editingId:"")');if(id)modal.dataset.editId=String(id)}catch(err){}},40);
    },true);
    form.addEventListener('submit',function(e){
      const id=modal.dataset.editId||(function(){try{return eval('(typeof editingId!=="undefined"?editingId:"")')}catch(err){return ''}})();
      if(!id)return;
      e.preventDefault();e.stopImmediatePropagation();
      let card=null;try{card=eval('cards.find(function(x){return x.id===id})')}catch(err){}
      if(!card)return;
      let prog;try{prog=eval('progress')}catch(err){try{prog=JSON.parse(localStorage.getItem(PROG_KEY)||'{}')}catch(e2){prog={}}}
      const val=n=>document.getElementById(n)?.value||'',word=val('editWord').trim();if(!word)return;
      const old=prog[id]||{},status=val('editStatus');
      const p=Object.assign({},old,{word,translation:val('editTranslation').trim(),level:val('editLevel')||card.level||'A1',line:val('editLine').trim(),lineTranslation:val('editLineEn').trim(),show:val('editShow').trim(),song:val('editSong').trim(),note:val('editNote').trim(),excluded:!!document.getElementById('editExclude')?.checked,mastered:status==='mastered',reps:status==='new'?0:(status==='learning'?Math.max(1,old.reps||0):(old.reps||0))});
      prog[id]=p;try{eval('progress=prog')}catch(err){};try{eval('save()')}catch(err){try{localStorage.setItem(PROG_KEY,JSON.stringify(prog))}catch(e2){}}
      Object.assign(card,p);try{eval('(typeof queue!=="undefined"?queue:[]).forEach(function(x){if(x&&x.id===id)Object.assign(x,card)})')}catch(err){}
      modal.classList.add('hidden');modal.dataset.editId='';try{eval('editingId=null')}catch(err){}
      try{eval('renderWords()')}catch(err){}try{eval('renderStudy()')}catch(err){}try{eval('renderWordsV3()')}catch(err){}
    },true);
  }

  function installBackAudio(){
    const session=document.getElementById('session');if(!session)return;
    const addButton=function(){
      const back=session.querySelector('.card .back');if(!back||back.querySelector('[data-manual-audio]'))return;
      const b=document.createElement('button');b.type='button';b.className='btn ghost';b.dataset.manualAudio='1';b.textContent='▶ Play audio';b.style.marginTop='14px';b.style.color='var(--paper)';b.style.borderColor='var(--gold)';
      b.onclick=function(e){e.preventDefault();e.stopPropagation();try{const a=eval('(typeof audio!=="undefined"?audio:null)');if(a){a.currentTime=0;const r=a.play();if(r?.catch)r.catch(console.error);return}const c=eval('(typeof queue!=="undefined"&&typeof idx!=="undefined"?queue[idx]:null)');if(typeof play==='function'&&c)play(c)}catch(err){console.error('Flashcard audio error:',err)}};
      back.appendChild(b);
    };
    new MutationObserver(addButton).observe(session,{childList:true,subtree:true});addButton();
  }

  loadOriginal(function(){setTimeout(function(){installEditorRepair();installBackAudio();installPreferenceSaving()},0)});
})();
