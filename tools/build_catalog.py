from pathlib import Path
import json, re
from datetime import datetime, timezone

ROOT=Path('.')
MUSIC=ROOT/'music'
OUT=ROOT/'data/catalog.json'
AUDIO_EXTS={'.mp3','.m4a','.wav','.ogg','.aac'}
COMMON=set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())
LEVELS=['A1','A2','B1','B2','C1','C2']

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-') or 'item'
def clean_title(name): return re.sub(r'^\d+[\s._-]*','',Path(name).stem).strip()
def stem(name):
    s=Path(name).stem.lower().replace('´',"'").replace('’',"'")
    return re.sub(r'\s+',' ',s).strip()
def word_tokens(text):
    return re.findall(r"[A-Za-zÄÖÜäöüßÀ-ÿ]+(?:['’][A-Za-zÄÖÜäöüßÀ-ÿ]+)?",text)
def norm_word(w): return re.sub(r"[^A-Za-zÄÖÜäöüßÀ-ÿ'-]",'',w).strip("'-")
def lemma(w):
    x=norm_word(w); l=x.lower()
    m={'bin':'sein','bist':'sein','ist':'sein','sind':'sein','seid':'sein','war':'sein','waren':'sein','habe':'haben','hast':'haben','hat':'haben','habt':'haben','hatte':'haben','hatten':'haben','kann':'können','kannst':'können','könnt':'können','konnte':'können','muss':'müssen','musst':'müssen','musste':'müssen','mussten':'müssen','will':'wollen','willst':'wollen','wollt':'wollen','wollte':'wollen','wollten':'wollen','wird':'werden','wirst':'werden','wurde':'werden','finde':'finden','findest':'finden','findet':'finden','fand':'finden','geht':'gehen','ging':'gehen','kommt':'kommen','kam':'kommen','sagte':'sagen','sagt':'sagen','sah':'sehen','gesehen':'sehen','gibt':'geben','gab':'geben','nahm':'nehmen','genommen':'nehmen','macht':'machen','machte':'machen','gemacht':'machen','liebt':'lieben','liebte':'lieben','geliebt':'lieben','gesagt':'sagen','gesprochen':'sprechen','versteht':'verstehen','verstanden':'verstehen','verloren':'verlieren','gewonnen':'gewinnen','geträumt':'träumen','weinte':'weinen','gelacht':'lachen','singt':'singen','getanzt':'tanzen','steht':'stehen','gestanden':'stehen','sitzt':'sitzen','liegt':'liegen'}
    return m.get(l,x)
def parse_lrc(path):
    lines=[]
    for raw in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        tags=list(re.finditer(r'\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]',raw))
        clean=re.sub(r'\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]','',raw).strip()
        if not clean or not tags: continue
        for t in tags:
            sec=int(t.group(1))*60+int(t.group(2))+int((t.group(3) or '0').ljust(3,'0'))/1000
            lines.append({'text':clean,'time':round(sec,3)})
    lines.sort(key=lambda x:x['time'])
    for i,x in enumerate(lines): x['endTime']=lines[i+1]['time'] if i+1<len(lines) else x['time']+4.5
    return lines

def parse_index_dict():
    p=ROOT/'index.html'
    if not p.exists(): return {}
    text=p.read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'const\s+GERMAN_DICT\s*=\s*\{(.*?)\n\};',text,re.S)
    if not m: return {}
    d={}
    for k,en,lv in re.findall(r'"([^"]+)"\s*:\s*\{en:"([^"]*)",level:(\d+)\}',m.group(1)):
        d[k.lower()]={'en':en,'level':LEVELS[int(lv)-1] if 1<=int(lv)<=6 else 'B1'}
    return d

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    old={}
    if OUT.exists():
        try: old=json.loads(OUT.read_text(encoding='utf-8'))
        except: pass
    old_cards={c.get('id'):c for c in old.get('cards',[]) if isinstance(c,dict) and c.get('id')}
    dictionary=parse_index_dict()
    musicals=[]; cards=[]
    for md in sorted([p for p in MUSIC.iterdir() if p.is_dir() and not p.name.startswith('.')],key=lambda p:p.name.lower()) if MUSIC.exists() else []:
        lrcs={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower()=='.lrc'}
        audios={stem(p.name):p for p in md.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS}
        songs=[]
        for key,lp in sorted(lrcs.items()):
            ap=audios.get(key)
            sid=f'{slug(md.name)}::{slug(clean_title(lp.name))}'
            songs.append({'id':sid,'title':clean_title(lp.name),'musical':md.name,'lrc':lp.as_posix(),'audio':ap.as_posix() if ap else ''})
            lines=parse_lrc(lp)
            first={}
            for line in lines:
                for raww in word_tokens(line['text']):
                    w=norm_word(raww); lem=lemma(w); k=lem.lower()
                    if len(k)<2 or k in COMMON: continue
                    first.setdefault(k,(lem,line))
            for k,(w,line) in first.items():
                h=dictionary.get(k) or dictionary.get(w.lower())
                oldid=f'builtin::{md.name}::{sid}::{k}'
                oldc=old_cards.get(oldid,{})
                cards.append({
                    'id':oldid,'word':w,'translation':h['en'] if h else oldc.get('translation',''),'lineTranslation':oldc.get('lineTranslation',''),
                    'level':h['level'] if h else oldc.get('level','B1'),'mastered':oldc.get('mastered',False),'excluded':oldc.get('excluded',False),
                    'musical':md.name,'show':md.name,'song':clean_title(lp.name),'line':line['text'],'startTime':line['time'],'endTime':line['endTime'],
                    'audioUrl':ap.as_posix() if ap else '','source':'builtin','reps':oldc.get('reps',0),'box':oldc.get('box',0),'dueDate':oldc.get('dueDate'),
                    'lastReviewed':oldc.get('lastReviewed'),'created':oldc.get('created',datetime.now(timezone.utc).timestamp()*1000)
                })
        musicals.append({'id':slug(md.name),'name':md.name,'description':'','songs':songs})
    data={'version':datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'updatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'musicals':musicals,'cards':cards}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built {len(musicals)} musicals, {sum(len(m["songs"]) for m in musicals)} songs, {len(cards)} vocabulary cards.')
if __name__=='__main__': main()
