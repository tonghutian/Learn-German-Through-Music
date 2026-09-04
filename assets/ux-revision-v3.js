(function(){
  'use strict';

  function loadOriginal(done){
    const s=document.createElement('script');
    s.src='assets/ux-revision-v3-original.js?v=5';
    s.onload=done;
    s.onerror=function(){console.error('Could not load original study UI')};
    document.head.appendChild(s);
  }

  function installEditor(){
    const form=document.getElementById('editForm');
    const modal=document.getElementById('editModal');
    if(!form || !modal) return;
    if(form.dataset.editorInstalled==='1') return;
    form.dataset.editorInstalled='1';

    form.addEventListener('submit',function(e){
      e.preventDefault();
      e.stopPropagation();

      const id=window.editingId;
      if(!id) return;
      const c=(window.cards||[]).find(function(x){return x.id===id});
      if(!c) return;

      const p=Object.assign({}, (window.progress&&window.progress[id]) || {});
      const get=function(name){
        const el=document.getElementById(name);
        return el ? el.value : '';
      };

      const word=get('editWord').trim();
      if(!word){document.getElementById('editWord').focus();return;}

      p.word=word;
      p.translation=get('editTranslation').trim();
      p.level=get('editLevel') || c.level || 'A1';
      p.line=get('editLine').trim();
      p.lineTranslation=get('editLineEn').trim();
      p.show=get('editShow').trim();
      p.song=get('editSong').trim();
      p.note=get('editNote').trim();
      p.excluded=!!document.getElementById('editExclude')?.checked;

      const status=get('editStatus');
      p.mastered=status==='mastered';
      p.reps=status==='new' ? 0 : (status==='learning' ? Math.max(1,p.reps||0) : (p.reps||0));

      window.progress[id]=p;
      if(typeof window.save==='function') window.save();
      else localStorage.setItem('ldm-progress-v4',JSON.stringify(window.progress));

      Object.assign(c,{
        word:p.word,translation:p.translation,level:p.level,line:p.line,
        lineTranslation:p.lineTranslation,show:p.show,song:p.song,note:p.note,
        excluded:p.excluded,mastered:p.mastered,reps:p.reps
      });

      [window.queue||[]].forEach(function(list){
        list.forEach(function(x){
          if(x && x.id===id) Object.assign(x,c);
        });
      });

      modal.classList.add('hidden');
      window.editingId=null;

      if(typeof window.renderWords==='function') window.renderWords();
      if(typeof window.renderStudy==='function') window.renderStudy();
      if(typeof window.renderCard==='function' && window.queue && window.queue.some(function(x){return x.id===id})) window.renderCard();
    },true);
  }

  loadOriginal(function(){
    setTimeout(installEditor,0);
  });
})();