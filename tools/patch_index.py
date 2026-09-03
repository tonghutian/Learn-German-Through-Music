from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
# Library-first public interface: keep the private import feature in the codebase but hide it from the built-in site.
s=s.replace('''    <button data-tab="library" class="active">Library</button>\n    <button data-tab="import">Import</button>\n    <button data-tab="table">All Words</button>\n    <button data-tab="study">Study</button>''','''    <button data-tab="library" class="active">Library</button>\n    <button data-tab="table">All Words</button>\n    <button data-tab="study">Study</button>''')
s=s.replace('<section class="panel" id="view-import">','<section class="panel" id="view-import" style="display:none;">',1)
# Built-in catalog cards use remote audioUrl; the old check only looked in the local upload map.
s=s.replace('const hasAudio = !!findAudioForSong(c.song) && c.startTime!=null;','const hasAudio = !!(c.audioUrl || findAudioForSong(c.song)) && c.startTime!=null;',1)
# Built-in song buttons should not try to click a hidden Import tab. Keep the function usable for compatibility.
s=s.replace("    document.querySelector('[data-tab=\"import\"]').click();\n    renderLrcLines();", "    const studyTab=document.querySelector('[data-tab=\"study\"]');\n    if(studyTab) studyTab.click();\n    renderLrcLines();",1)
# Make the public library explain the two modes without exposing the owner-only catalog editing workflow.
s=s.replace('''      <b>For site owners:</b> edit <code>data/catalog.json</code> in the GitHub repository. When you publish a new catalog version, users automatically receive the updated word meanings, English sentence translations, CEFR levels, and song metadata on their next visit.''','''      Built-in songs are published by the site owner. Your study progress and personal edits stay in this browser.''',1)
# Add a direct owner-maintained library status line if not already present.
s=s.replace('Premade content is loaded from this website\'s public catalog. Your learning progress stays on your computer.','Choose a Musical from the library. Your learning progress and personal edits stay on your computer.',1)
p.write_text(s,encoding='utf-8')
print('Patched index.html for library-first built-in music, remote audio, and private local progress.')
