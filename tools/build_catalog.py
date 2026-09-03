from pathlib import Path
import json, re, urllib.request
from datetime import datetime, timezone

ROOT=Path('.')
MUSIC=ROOT/'music'
DATA=ROOT/'data'
OUT=DATA/'catalog.json'
CARDS=DATA/'musicals'
AUDIO_EXTS={'.mp3','.m4a','.wav','.ogg','.aac'}
COMMON=set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())
LEVELS=['A1','A2','B1','B2','C1','C2']
PRIVATE_SOURCE='https://raw.githubusercontent.com/tonghutian/german/main/index.html'
BEOLINGUS_SOURCE='https://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt'

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-') or 'item'
def title(s): return re.sub(r'^\d+[\s._-]*','',Path(s).stem).strip()
def stem(s): return re.sub(r'\s+',' ',Path(s).stem.lower().replace('’',"'")).strip()
def tokens(s): return re.findall(r'[A-Za-zÄÖÜäöüßÀ-ÿ]+(?:[’\'][A-Za-zÄÖÜäöüßÀ-ÿ]+)?',s)
def lemma(w):
 l=w.lower(); m={'bin':'sein','bist':'sein','ist':'sein','sind':'sein','seid':'sein','war':'sein','waren':'sein','habe':'haben','hast':'haben','hat':'haben','habt':'haben','hatte':'haben','hatten':'haben','kann':'können','kannst':'können','könnt':'können','konnte':'können','muss':'müssen','musst':'müssen','musste':'müssen','mussten':'müssen','will':'wollen','willst':'wollen','wollt':'wollen','wollte':'wollen','wollten':'wollen','wird':'werden','wirst':'werden','wurde':'werden','finde':'finden','findest':'finden','findet':'finden','fand':'finden','geht':'gehen','ging':'gehen','kommt':'kommen','kam':'kommen','sagte':'sagen','sagt':'sagen','sah':'sehen','gesehen':'sehen','gibt':'geben','gab':'geben','nahm':'nehmen','genommen':'nehmen','macht':'machen','machte':'machen','gemacht':'machen','liebt':'lieben','liebte':'lieben','geliebt':'lieben','gesagt':'sagen','gesprochen':'sprechen','versteht':'verstehen','verstanden':'verstehen','verloren':'verlieren','gewonnen':'gewinnen','geträumt':'träumen','weinte':'weinen','gelacht':'lachen','singt':'singen','getanzt':'tanzen','steht':'stehen','gestanden':'stehen','sitzt':'sitzen','liegt':'liegen'}; return m.get(l,w)
def lrc(path):
 out=[]
 for raw in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
  tags=list(re.finditer(r'\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]',raw)); clean=re.sub(r'\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]','',raw).strip()
  if not clean or not tags: continue
  for t in tags: out.append({'text':clean,'time':int(t.group(1))*60+int(t.group(2))+int((t.group(3) or '0').ljust(3,'0'))/1000})
 out.sort(key=lambda x:x['time'])
 for i,x in enumerate(out): x['endTime']=out[i+1]['time'] if i+1<len(out) else x['time']+4.5
 return out

def level_for(word, hit=None):
 if hit and hit.get('level') in LEVELS: return hit['level']
 w=word.lower();
 if hit and hit.get('level') in range(1,7): return LEVELS[hit['level']-1]
 if w in COMMON or len(w)<=3: return 'A1'
 if len(w)<=5: return 'A2'
 if len(w)<=8: return 'B1'
 if len(w)<=11: return 'B2'
 if len(w)<=14: return 'C1'
 return 'C2'

def extract_private_dict():
 try:
  text=urllib.request.urlopen(PRIVATE_SOURCE,timeout=30).read().decode('utf-8','ignore')
  m=re.search(r'const\s+GERMAN_DICT\s*=\s*\{(.*?)\n\};',text,re.S)
  if not m: return {}
  d={}
  for k,en,lv in re.findall(r'\\?"([^"]+)\\?"\s*:\s*\{en:\\?"([^"]*)\\?",level:(\d+)\}',m.group(1)):
   d[k.lower()]={'en':en,'level':int(lv)}
  return d
 except Exception as e:
  print('Private dictionary unavailable:',e); return {}

def parse_beolingus_line(line):
 parts=line.split('::')
 if len(parts)<2: return []
 de_groups=parts[0].strip().split('|')
 en_groups='::'.join(parts[1:]).strip().split('|')
 out=[]
 for gi,dg in enumerate(de_groups):
  en_raw=(en_groups[gi] if gi<len(en_groups) else (en_groups[0] if en_groups else '')).strip()
  en_raw=re.sub(r'\{[^}]*\}|\[[^]]*\]|<[^>]*>','',en_raw)
  en_parts=[x.strip() for x in re.split(r'[;|]',en_raw) if x.strip()]
  if not en_parts: continue
  gloss='; '.join(en_parts[:2])[:70]
  for alt in dg.split(';'):
   de=re.sub(r'\{[^}]*\}|\[[^]]*\]|\([^)]*\)',' ',alt).strip().lower()
   if not de or re.search(r'\s',de): continue
   de=re.sub(r"[^a-zäöüßéèêàáâëïöü'-]",'',de)
   if 2<=len(de)<=35: out.append((de,gloss))
 return out

def load_beolingus(target_words):
 if not target_words: return {}
 try:
  req=urllib.request.Request(BEOLINGUS_SOURCE,headers={'User-Agent':'Learn-German-Through-Music/1.0'})
  text=urllib.request.urlopen(req,timeout=60).read().decode('utf-8','ignore')
  hits={}
  for line in text.splitlines():
   for de,en in parse_beolingus_line(line):
    if de in target_words and de not in hits: hits[de]=en
  print(f'Beolingus filled {len(hits)} additional word(s).')
  return hits
 except Exception as e:
  print('Beolingus unavailable:',e); return {}

def main():
 DATA.mkdir(exist_ok=True); CARDS.mkdir(exist_ok=True)
 private=extract_private_dict()
 musicals=[]
 for md in sorted([p for p in MUSIC.iterdir() if p.is_dir() and not p.name.startswith('.')],key=lambda p:p.name.lower()) if MUSIC.exists() else []:
  mid=slug(md.name); old_path=CARDS/f'{mid}.json'; old_cards={}
  if old_path.exists():
   try: old_cards={c['id']:c for c in json.loads(old_path.read_text(encoding='utf-8')).get('cards',[])}
   except Exception: old_cards={}
  lrcs={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower()=='.lrc'}
  aud={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS}
  songs=[]; cards=[]; unresolved=set()
  for k,lp in sorted(lrcs.items()):
   ap=aud.get(k); sid=f'{mid}::{slug(title(lp.name))}'
   songs.append({'id':sid,'title':title(lp.name),'musical':md.name,'lrc':lp.as_posix(),'audio':ap.as_posix() if ap else ''})
   lines=lrc(lp); first={}
   for line in lines:
    for raw in tokens(line['text']):
     w=lemma(raw); key=w.lower()
     if len(key)>=2 and key not in COMMON: first.setdefault(key,(w,line))
   for key,(w,line) in first.items():
    cid=f'builtin::{md.name}::{sid}::{key}'; old=old_cards.get(cid,{})
    hit=private.get(key) or private.get(w.lower())
    translation=(old.get('translation') or '').strip() or (hit.get('en','') if hit else '')
    if not translation: unresolved.add(key)
    old_level=old.get('level')
    level=old_level if old_level in LEVELS else level_for(w,hit)
    cards.append({
      'id':cid,'word':w,'translation':translation,'lineTranslation':old.get('lineTranslation',''),'level':level,
      'mastered':False,'excluded':False,'musical':md.name,'show':md.name,'song':title(lp.name),
      'line':line['text'],'startTime':line['time'],'endTime':line['endTime'],'audioUrl':ap.as_posix() if ap else '','source':'builtin'
    })
  # Fill only genuinely missing word translations from Beolingus. This is done after the private site's dictionary so it matches the uploader first.
  extra=load_beolingus(unresolved) if unresolved else {}
  for c in cards:
   if not c['translation']:
    en=extra.get(c['word'].lower(),'')
    if en: c['translation']=en
    if not c['level'] or c['level'] not in LEVELS: c['level']=level_for(c['word'])
  counts={x:0 for x in LEVELS}
  for c in cards: counts[c['level'] if c['level'] in counts else 'B1']+=1
  old_version=''
  if old_path.exists():
   try: old_version=json.loads(old_path.read_text(encoding='utf-8')).get('version','')
   except: pass
  if cards:
   old_path.write_text(json.dumps({'version':datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'musical':md.name,'cards':cards},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
  musicals.append({'id':mid,'name':md.name,'description':'','cardsUrl':f'data/musicals/{mid}.json','cardCount':len(cards),'levelCounts':counts,'songs':songs})
 data={'version':datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'updatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'musicals':musicals}
 OUT.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(f'Built {len(musicals)} musicals and {sum(len((CARDS/f"{m["id"]}.json").read_text(encoding="utf-8")) for m in musicals if False)} cards.')
if __name__=='__main__': main()
