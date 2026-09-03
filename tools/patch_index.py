from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
# Library-first public interface: keep the private import feature in the codebase but hide it from the built-in site.
s=s.replace('''    <button data-tab="library" class="active">Library</button>\n    <button data-tab="import">Import</button>\n    <button data-tab="table">All Words</button>\n    <button data-tab="study">Study</button>''','''    <button data-tab="library" class="active">Library</button>\n    <button data-tab="table">All Words</button>\n    <button data-tab="study">Study</button>''')
s=s.replace('<section class="panel" id="view-import">','<section class="panel" id="view-import" style="display:none;">',1)
s=s.replace('const hasAudio = !!findAudioForSong(c.song) && c.startTime!=null;','const hasAudio = !!(c.audioUrl || findAudioForSong(c.song)) && c.startTime!=null;',1)
s=s.replace("    document.querySelector('[data-tab=\"import\"]').click();\n    renderLrcLines();", "    const studyTab=document.querySelector('[data-tab=\"study\"]');\n    if(studyTab) studyTab.click();\n    renderLrcLines();",1)
s=s.replace('''      <b>For site owners:</b> edit <code>data/catalog.json</code> in the GitHub repository. When you publish a new catalog version, users automatically receive the updated word meanings, English sentence translations, CEFR levels, and song metadata on their next visit.''','''      Built-in songs are published by the site owner. Your study progress and personal edits stay in this browser.''',1)
s=s.replace('Premade content is loaded from this website\'s public catalog. Your learning progress stays on your computer.','Choose a Musical from the library. Your learning progress and personal edits stay on your computer.',1)

marker='<!-- study-ux-v2 -->'
if marker not in s:
    backup_ui='''<div class="notice" style="margin-top:18px;text-align:center">\n<strong>Saved data</strong><br>\n<span class="tiny">Download a backup of your study progress and personal edits, or restore them later.</span>\n<div class="row" style="justify-content:center;margin-top:9px">\n<button class="btn ghost" id="downloadSavedData" type="button">Download saved data</button>\n<button class="btn ghost" id="restoreSavedData" type="button">Restore saved data</button>\n<input id="restoreSavedDataFile" type="file" accept="application/json,.json" class="hidden">\n</div></div>\n'''
    footer='<p style="text-align:center;color:#dfc09a;font-size:13px;margin-top:16px">For your own private uploads, use <a href="https://tonghutian.github.io/german/" style="color:#e5c477;font-weight:700">the private uploader</a>.</p>'
    footer_new='<p style="text-align:center;color:#dfc09a;font-size:13px;margin-top:16px">For your own private uploads, use <a href="https://tonghutian.github.io/german/" target="_blank" rel="noopener noreferrer" style="color:#e5c477;font-weight:700">the private uploader</a>.</p>'
    if footer in s:s=s.replace(footer,backup_ui+footer_new,1)
    else:s=s.replace('</body>',backup_ui+footer_new+'</body>',1)
    inject=r'''<!-- study-ux-v2 -->
<script>
(function(){
  function downloadSavedData(){
    const payload={version:2,app:'Learn German Through Music',exportedAt:new Date().toISOString(),progress:progress,settings:{active:active,levels:[...levels],studyMode:$('studyMode')?.value||'due',studyOrder:$('studyOrder')?.value||'level'}};
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='learn-german-through-music-backup.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function restoreSavedData(file){
    const data=JSON.parse(await file.text());
    const incoming=data&&data.progress&&typeof data.progress==='object'?data.progress:null;
    if(!incoming)throw Error('This file does not contain saved study data.');
    localStorage.setItem(PROG,JSON.stringify(incoming));
    alert('Saved data restored. The page will reload.');location.reload();
  }
  function wireBackup(){
    const d=$('downloadSavedData'),r=$('restoreSavedData'),f=$('restoreSavedDataFile');
    if(d)d.onclick=downloadSavedData;
    if(r&&f){r.onclick=()=>f.click();f.onchange=()=>{const file=f.files?.[0];if(!file)return;restoreSavedData(file).catch(e=>alert('Could not restore this file: '+e.message)).finally(()=>f.value='');};}
  }
  let lastId=null,lastNode=null;
  function syncStudyCard(){
    const session=$('session');const cardEl=session?.querySelector('.card');
    if(!cardEl){if(lastNode){stop();lastNode=null;lastId=null;}return;}
    const c=queue[idx];if(!c)return;
    if(c.id===lastId&&cardEl===lastNode)return;
    stop();lastId=c.id;lastNode=cardEl;
    setTimeout(()=>{const now=$('session')?.querySelector('.card');if(now===cardEl&&queue[idx]?.id===c.id)play(c);},120);
    const title=c.song||c.show||c.musical||'';
    if(title&&!cardEl.querySelector('[data-song-name]')){
      const label=document.createElement('div');label.dataset.songName='1';label.className='tiny';label.style.marginTop='9px';label.textContent='Song: '+title;
      const front=cardEl.querySelector('.front');if(front)front.appendChild(label);
    }
  }
  function observe(){
    const s=$('session');if(!s)return;
    new MutationObserver(syncStudyCard).observe(s,{childList:true,subtree:true});
    setInterval(syncStudyCard,250);
  }
  wireBackup();observe();
})();
</script>
'''
    s=s.replace('</body>',inject+'</body>',1)

p.write_text(s,encoding='utf-8')
print('Patched index.html for library-first built-in music, remote audio, private local progress, automatic study audio, song labels, backup/restore, and new-tab private uploads.')
