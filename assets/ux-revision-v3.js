(function(){
  'use strict';

  function loadOriginal(done){
    const s=document.createElement('script');
    s.src='assets/ux-revision-v3-original.js?v=7';
    s.onload=done;
    s.onerror=function(){console.error('Could not load original study UI')};
    document.head.appendChild(s);
  }

  function installEditor(){
    const form=document.getElementById('editForm');
    const modal=document.getElementById('editModal');
    if(!form || !modal) return;
    if(form.dataset.editorRepairInstalled==='1') return;
    form.dataset.editorRepairInstalled='1';

    document.addEventListener('click',function(e){
      const button=e.target.closest && e.target.closest('[data-edit],#editStudyBtn');
      if(!button) return;
      let id=button.getAttribute('data-edit') || '';
      if(!id){
        try { id=eval('(typeof queue!=="undefined" && queue[idx]) ? queue[idx].id : ""'); } catch(err) {}
      }
      if(id) modal.dataset.editId=String(id);
    },true);

    form.addEventListener('submit',function(e){
      e.preventDefault();
      e.stopImmediatePropagation();

      const id=modal.dataset.editId || '';
      if(!id) return;

      let card, prog;
      try { card=eval('cards.find(function(x){return x.id===id})'); } catch(err) { console.error(err); return; }
      if(!card) return;
      try { prog=eval('progress'); } catch(err) { prog={}; }

      const val=function(name){const el=document.getElementById(name);return el?el.value:''};
      const word=val('editWord').trim();
      if(!word){document.getElementById('editWord').focus();return;}

      const old=prog[id] || {};
      const p=Object.assign({},old,{
        word:word,
        translation:val('editTranslation').trim(),
        level:val('editLevel') || card.level || 'A1',
        line:val('editLine').trim(),
        lineTranslation:val('editLineEn').trim(),
        show:val('editShow').trim(),
        song:val('editSong').trim(),
        note:val('editNote').trim(),
        excluded:!!document.getElementById('editExclude')?.checked
      });
      const status=val('editStatus');
      p.mastered=status==='mastered';
      p.reps=status==='new'?0:(status==='learning'?Math.max(1,old.reps||0):(old.reps||0));

      prog[id]=p;
      try { eval('save()'); } catch(err) { localStorage.setItem('ldm-progress-v4',JSON.stringify(prog)); }

      Object.assign(card,{
        word:p.word,translation:p.translation,level:p.level,line:p.line,
        lineTranslation:p.lineTranslation,show:p.show,song:p.song,note:p.note,
        excluded:p.excluded,mastered:p.mastered,reps:p.reps
      });

      try { eval('(typeof queue!=="undefined"?queue:[]).forEach(function(x){if(x&&x.id===id)Object.assign(x,card)})'); } catch(err) {}
      try { eval('(typeof groupWords!=="undefined"?groupWords:[]).forEach(function(x){if(x&&x.id===id)Object.assign(x,card)})'); } catch(err) {}
      try { eval('(typeof studyQueue!=="undefined"?studyQueue:[]).forEach(function(x){if(x&&x.id===id)Object.assign(x,card)})'); } catch(err) {}

      modal.classList.add('hidden');
      modal.dataset.editId='';
      try { eval('editingId=null'); } catch(err) {}

      try { eval('renderWords()'); } catch(err) {}
      try { eval('renderStudy()'); } catch(err) {}
      try { eval('if(typeof renderCard===\"function\" && typeof queue!==\"undefined\" && queue.some(function(x){return x.id===id}))renderCard()'); } catch(err) {}
    },true);
  }

  loadOriginal(function(){setTimeout(installEditor,0)});
})();