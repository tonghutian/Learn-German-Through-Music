(function(){
  'use strict';

  const PREF_KEY='ldm-study-preferences-v2';

  function readPrefs(){
    try{return JSON.parse(localStorage.getItem(PREF_KEY)||'{}')||{}}catch(e){return {}}
  }
  function writePrefs(p){
    try{localStorage.setItem(PREF_KEY,JSON.stringify(p))}catch(e){}
  }

  // IMPORTANT: index.html already contains the working Study implementation.
  // Do not load a second copy of the Study code: that caused two competing
  // renderers/event handlers and was the source of the broken Musical/Edit/audio behavior.

  function rememberChoices(){
    const musical=document.getElementById('studyMusical');
    const mode=document.getElementById('studyMode');
    const order=document.getElementById('studyOrder');
    const levels=[...document.querySelectorAll('#studyLevels .pill.active')]
      .map(b=>b.dataset.level||b.textContent.trim()).filter(Boolean);
    const p=readPrefs();
    if(musical) p.musical=musical.value||'';
    if(mode) p.mode=mode.value||'due';
    if(order) p.order=order.value||'random';
    p.levels=levels;
    p.savedAt=Date.now();
    writePrefs(p);
  }

  let restored=false;
  function restoreChoices(){
    if(restored)return;
    const p=readPrefs();
    const musical=document.getElementById('studyMusical');
    const mode=document.getElementById('studyMode');
    const order=document.getElementById('studyOrder');
    if(!musical||!musical.options||musical.options.length<2)return;

    if(p.mode && [...mode.options].some(o=>o.value===p.mode)) mode.value=p.mode;
    // Shuffle is the default Study order. Keep an explicitly saved user choice,
    // but use Random when there is no saved preference yet.
    if(p.order && [...order.options].some(o=>o.value===p.order)){
      order.value=p.order;
    }else if([...order.options].some(o=>o.value==='random')){
      order.value='random';
    }

    if(Array.isArray(p.levels)){
      const want=new Set(p.levels.map(String));
      const pills=[...document.querySelectorAll('#studyLevels .pill')];
      pills.forEach(b=>{
        const should=want.has(String(b.dataset.level||b.textContent.trim()));
        const is=b.classList.contains('active');
        if(should!==is)b.click();
      });
    }

    // Only restore a saved musical if it still exists in the current catalog.
    // This prevents the "Musical not found" popup from stale localStorage data.
    if(p.musical && [...musical.options].some(o=>o.value===p.musical)){
      musical.value=p.musical;
      if(typeof window.loadActive==='function'){
        restored=true;
        window.loadActive(p.musical,'study').catch?.(()=>{});
      }
    }else{
      restored=true;
      if(!p.musical) rememberChoices();
    }
  }

  function installPreferenceSaving(){
    ['studyMusical','studyMode','studyOrder'].forEach(id=>{
      document.getElementById(id)?.addEventListener('change',()=>setTimeout(rememberChoices,20),true);
    });
    document.addEventListener('click',e=>{
      if(e.target.closest?.('#studyLevels .pill'))setTimeout(rememberChoices,30);
      if(e.target.closest?.('#start'))setTimeout(rememberChoices,30);
      if(e.target.closest?.('[data-view="study"]'))setTimeout(restoreChoices,80);
    },true);
    // catalog.json is loaded asynchronously by index.html, so wait for its options.
    const timer=setInterval(()=>{
      if(document.querySelectorAll('#studyMusical option').length>1){
        clearInterval(timer); restoreChoices();
      }
    },100);
    setTimeout(()=>clearInterval(timer),10000);
  }

  function installBackAudio(){
    const session=document.getElementById('session');
    if(!session)return;

    const addButton=()=>{
      const back=session.querySelector('.card .back');
      if(!back || back.querySelector('[data-manual-audio]'))return;
      const b=document.createElement('button');
      b.type='button';
      b.className='btn ghost';
      b.dataset.manualAudio='1';
      b.textContent='▶ Play audio';
      b.style.marginTop='14px';
      b.style.color='var(--paper)';
      b.style.borderColor='var(--gold)';
      b.onclick=e=>{
        e.preventDefault();
        e.stopPropagation();
        // index.html's native Study card already has #listen wired to play(c).
        // Reuse that exact handler so the correct word/song/time is preserved.
        const listen=document.getElementById('listen');
        if(listen)listen.click();
      };
      back.appendChild(b);
    };

    new MutationObserver(addButton).observe(session,{childList:true,subtree:true});
    addButton();
  }

  function init(){
    installBackAudio();
    installPreferenceSaving();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();
