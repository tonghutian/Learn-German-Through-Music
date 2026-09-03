from pathlib import Path
import json, re
from datetime import datetime, timezone
ROOT=Path('.')
MUSIC=ROOT/'music'
DATA=ROOT/'data'
OUT=DATA/'catalog.json'
CARDS=DATA/'musicals'
AUDIO_EXTS={'.mp3','.m4a','.wav','.ogg','.aac'}
COMMON=set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())
LEVELS=['A1','A2','B1','B2','C1','C2']
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-') or 'item'
def title(s): return re.sub(r'^\d+[\s._-]*','',Path(s).stem).strip()
def stem(s): return re.sub(r'\s+',' ',Path(s).stem.lower().replace('’',"'")).strip()
def tokens(s): return re.findall(r'[A-Za-zÄÖÜäöüßÀ-ÿ]+',s)
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
def dictionary():
 p=ROOT/'index.html'; d={}
 if not p.exists(): return d
 m=re.search(r'const\s+GERMAN_DICT\s*=\s*\{(.*?)\n\};',p.read_text(encoding='utf-8',errors='ignore'),re.S)
 if m:
  for k,en,lv in re.findall(r'"([^"]+)"\s*:\s*\{en:"([^"]*)",level:(\d+)\}',m.group(1)): d[k.lower()]={'en':en,'level':LEVELS[int(lv)-1] if 1<=int(lv)<=6 else 'B1'}
 return d
def main():
 DATA.mkdir(exist_ok=True); CARDS.mkdir(exist_ok=True); d=dictionary(); musicals=[]
 for md in sorted([p for p in MUSIC.iterdir() if p.is_dir() and not p.name.startswith('.')],key=lambda p:p.name.lower()) if MUSIC.exists() else []:
  lrcs={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower()=='.lrc'}; aud={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS}; songs=[]; cards=[]
  for k,lp in sorted(lrcs.items()):
   ap=aud.get(k); sid=f'{slug(md.name)}::{slug(title(lp.name))}'; songs.append({'id':sid,'title':title(lp.name),'musical':md.name,'lrc':lp.as_posix(),'audio':ap.as_posix() if ap else ''})
   lines=lrc(lp); first={}
   for line in lines:
    for raw in tokens(line['text']):
     w=lemma(raw); key=w.lower()
     if len(key)>=2 and key not in COMMON: first.setdefault(key,(w,line))
   for key,(w,line) in first.items():
    h=d.get(key) or d.get(w.lower()); cards.append({'id':f'builtin::{md.name}::{sid}::{key}','word':w,'translation':h['en'] if h else '','lineTranslation':'','level':h['level'] if h else 'B1','mastered':False,'excluded':False,'musical':md.name,'show':md.name,'song':title(lp.name),'line':line['text'],'startTime':line['time'],'endTime':line['endTime'],'audioUrl':ap.as_posix() if ap else '','source':'builtin'})
  mid=slug(md.name); (CARDS/f'{mid}.json').write_text(json.dumps({'version':datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'musical':md.name,'cards':cards},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
  counts={x:0 for x in LEVELS}
  for c in cards: counts[c['level'] if c['level'] in counts else 'B1']+=1
  musicals.append({'id':mid,'name':md.name,'description':'','cardsUrl':f'data/musicals/{mid}.json','cardCount':len(cards),'levelCounts':counts,'songs':songs})
 OUT.write_text(json.dumps({'version':datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'updatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'musicals':musicals},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__': main()
