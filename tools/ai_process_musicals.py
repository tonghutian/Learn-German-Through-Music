#!/usr/bin/env python3
"""Process local German musical LRC files with a free local Ollama model.

Usage:
  python3 tools/ai_process_musicals.py --music-dir music --out-dir data/ai-reviewed

The script never touches MP3 files. It preserves LRC timestamps, asks the local
model to clean obvious lyric transcription errors, identify useful German
vocabulary, normalize lemmas, translate words and lines to English, and assign
CEFR levels. Existing approved JSON is used as a preservation source: non-empty
translation/level/lineTranslation fields are not overwritten.
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.request
from pathlib import Path

OLLAMA_URL='http://localhost:11434/api/chat'
LEVELS=['A1','A2','B1','B2','C1','C2']
FILLER=set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())
TOKEN_RE=re.compile(r"[A-Za-zÄÖÜäöüßÀ-ÿ]+(?:[’'][A-Za-zÄÖÜäöüßÀ-ÿ]+)?")
TIME_RE=re.compile(r'\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]')

def slug(s:str)->str:
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-') or 'item'

def title(path:Path)->str:
    return re.sub(r'^\d+[\s._-]*','',path.stem).strip()

def parse_lrc(path:Path):
    rows=[]
    for raw in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        tags=list(TIME_RE.finditer(raw))
        text=TIME_RE.sub('',raw).strip()
        if not tags or not text: continue
        for t in tags:
            ms=t.group(3) or '0'
            sec=int(t.group(1))*60+int(t.group(2))+int(ms.ljust(3,'0'))/1000
            rows.append({'time':round(sec,3),'text':text})
    rows.sort(key=lambda x:x['time'])
    for i,r in enumerate(rows): r['endTime']=rows[i+1]['time'] if i+1<len(rows) else round(r['time']+4.5,3)
    return rows

def pair_audio(lrc:Path):
    stem=lrc.stem.lower()
    for p in lrc.parent.iterdir():
        if p.is_file() and p.suffix.lower() in {'.mp3','.m4a','.wav','.ogg','.aac'} and p.stem.lower()==stem:
            return p
    return None

def call_ollama(model:str,prompt:str):
    payload={'model':model,'messages':[{'role':'system','content':'You are a careful German language editor for a vocabulary-learning app. Return ONLY valid JSON, no markdown.'},{'role':'user','content':prompt}], 'stream':False, 'options':{'temperature':0.1}}
    req=urllib.request.Request(OLLAMA_URL,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as r:
        data=json.loads(r.read().decode('utf-8'))
    text=((data.get('message') or {}).get('content') or '').strip()
    text=re.sub(r'^```json\s*|\s*```$','',text,flags=re.I).strip()
    try: return json.loads(text)
    except Exception:
        start=text.find('{'); end=text.rfind('}')
        if start>=0 and end>start: return json.loads(text[start:end+1])
        raise ValueError('Model did not return JSON')

def process_song(model, musical, lrc_path, existing_cards):
    lines=parse_lrc(lrc_path)
    # Work in chunks so long songs do not exceed local model context.
    out=[]
    for base in range(0,len(lines),35):
        chunk=lines[base:base+35]
        numbered=[{'i':base+i,'time':x['time'],'endTime':x['endTime'],'text':x['text']} for i,x in enumerate(chunk)]
        prompt=f'''Musical: {musical}\nSong: {title(lrc_path)}\n\nAnalyze these timestamped German lyric lines.\nReturn JSON exactly:\n{{"lines":[{{"i":0,"corrected":"...","english":"...","keep":true}}],"vocabulary":[{{"line_i":0,"surface":"geht","lemma":"gehen","english":"to go","cefr":"A1","type":"vocabulary"}}]}}\n\nRules:\n- Keep timestamps outside the model; do not invent timestamps.\n- Correct only obvious transcription/spelling errors; preserve meaning and wording.\n- Translate the ENTIRE lyric line naturally into English.\n- Extract useful German vocabulary learners should study. Exclude names, places, titles, speaker labels, interjections, fillers, and function words unless unusually useful.\n- Use the lemma/base form where appropriate (geht -> gehen, Kindern -> Kind).\n- CEFR must be A1/A2/B1/B2/C1/C2. Estimate from normal German learner difficulty and commonness; do NOT use word length as a proxy.\n- A compound or literary word can be B2/C1/C2 even if long; common short words can be A1.\n- If uncertain, choose the lower plausible level rather than defaulting to B1.\n- Keep only real German vocabulary.\n\nLines:\n{json.dumps(numbered,ensure_ascii=False)}'''
        ans=call_ollama(model,prompt)
        accepted_lines={int(x.get('i')):x for x in ans.get('lines',[]) if isinstance(x,dict) and str(x.get('i','')).isdigit()}
        voc=ans.get('vocabulary',[]) if isinstance(ans.get('vocabulary',[]),list) else []
        for idx,x in enumerate(chunk, start=base):
            a=accepted_lines.get(idx,{})
            out.append({'index':idx,'time':x['time'],'endTime':x['endTime'],'text':a.get('corrected') or x['text'],'english':a.get('english') or ''})
        time.sleep(0.1)
    by_key={}
    for i,line in enumerate(out):
        toks=TOKEN_RE.findall(line['text'])
        for tok in toks:
            k=tok.lower()
            if len(k)<2 or k in FILLER: continue
            by_key.setdefault(k,{'surface':tok,'line_index':i})
    # Ask the model for a final vocabulary pass on deduplicated candidates, chunked.
    vocab=[]
    candidates=list(by_key.values())
    for base in range(0,len(candidates),80):
        batch=candidates[base:base+80]
        prompt=f'''Create the final German learner vocabulary for {musical} / {title(lrc_path)}.\nReturn JSON only: {{"words":[{{"surface":"...","lemma":"...","english":"...","cefr":"A1","type":"vocabulary","line_index":0}}]}}\nRules:\n- Include only genuine useful German vocabulary from the candidates.\n- Exclude proper names, place names, song/title fragments, stage directions, punctuation, fillers, and grammatical noise.\n- Normalize inflected forms to a lemma.\n- Give a concise natural English meaning suitable for a flashcard.\n- CEFR A1-C2 based on learner difficulty/commonness, not length.\n- Prefer a lower level only when it is genuinely plausible; do not label everything B1.\nCandidates:\n{json.dumps(batch,ensure_ascii=False)}'''
        ans=call_ollama(model,prompt)
        for w in ans.get('words',[]) if isinstance(ans.get('words',[]),list) else []:
            if not isinstance(w,dict): continue
            lemma=str(w.get('lemma') or w.get('surface') or '').strip()
            en=str(w.get('english') or '').strip()
            lvl=str(w.get('cefr') or '').upper().strip()
            if not lemma or not en or lvl not in LEVELS: continue
            if w.get('type') not in (None,'vocabulary'): continue
            vocab.append({'word':lemma,'translation':en,'level':lvl,'line':out[int(w.get('line_index',0))]['text'] if str(w.get('line_index','0')).isdigit() and int(w.get('line_index',0))<len(out) else '','lineTranslation':out[int(w.get('line_index',0))]['english'] if str(w.get('line_index','0')).isdigit() and int(w.get('line_index',0))<len(out) else ''})
        time.sleep(0.1)
    cards={}
    for w in vocab:
        key=w['word'].lower()
        old=existing_cards.get(key,{})
        cards[key]={**w,'translation':old.get('translation') or w['translation'],'level':old.get('level') if old.get('level') in LEVELS else w['level'],'lineTranslation':old.get('lineTranslation') or w['lineTranslation']}
    audio=pair_audio(lrc_path)
    return lines,out,list(cards.values()),audio

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--music-dir',default='music')
    ap.add_argument('--out-dir',default='data/ai-reviewed')
    ap.add_argument('--model',default='qwen3:8b')
    args=ap.parse_args()
    music=Path(args.music_dir); outdir=Path(args.out_dir); outdir.mkdir(parents=True,exist_ok=True)
    # Probe Ollama before doing work.
    try: call_ollama(args.model,'Reply with {"ok":true}')
    except Exception as e:
        print('Ollama is not reachable. Install/start Ollama and run: ollama pull '+args.model, file=sys.stderr); raise
    for md in sorted([p for p in music.iterdir() if p.is_dir()],key=lambda p:p.name.lower()):
        existing={}
        oldpath=outdir/(slug(md.name)+'.json')
        if oldpath.exists():
            try: existing={c['word'].lower():c for c in json.loads(oldpath.read_text(encoding='utf-8')).get('cards',[])}
            except Exception: existing={}
        songs=[]; allcards=[]
        lrcs=sorted([p for p in md.iterdir() if p.is_file() and p.suffix.lower()=='.lrc'],key=lambda p:p.name.lower())
        for lp in lrcs:
            print(f'[{md.name}] {lp.name}')
            _,clean,words,audio=process_song(args.model,md.name,lp,existing)
            sid=f'{slug(md.name)}::{slug(title(lp))}'
            songs.append({'id':sid,'title':title(lp),'lrc':lp.as_posix(),'audio':audio.as_posix() if audio else ''})
            for w in words:
                w.update({'id':f'ai::{md.name}::{sid}::{w["word"].lower()}','musical':md.name,'show':md.name,'song':title(lp),'audioUrl':audio.as_posix() if audio else ''})
                allcards.append(w)
                existing[w['word'].lower()]=w
        # de-duplicate cards across songs while keeping the first useful line.
        uniq={}
        for c in allcards:
            uniq.setdefault(c['word'].lower(),c)
        cards=list(uniq.values())
        payload={'version':time.strftime('%Y%m%d-%H%M%S'),'musical':md.name,'songs':songs,'cards':cards}
        oldpath.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'  -> {len(songs)} songs, {len(cards)} vocabulary cards')
    print('DONE. Upload data/ai-reviewed/*.json to the site only after you have spot-checked them.')

if __name__=='__main__': main()
