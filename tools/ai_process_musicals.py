#!/usr/bin/env python3
"""Review German musical LRC files with a local Ollama model.

Designed for a MacBook: small requests, one song at a time, checkpoint after
EVERY song, and safe to stop/restart. It also writes corrected LRC files.

The Qwen3 model is explicitly run with thinking disabled. This is important:
otherwise Qwen3 may spend a very long time producing internal reasoning for
every lyric batch.
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.request
from pathlib import Path

OLLAMA_URL = 'http://localhost:11434/api/chat'
LEVELS = ['A1','A2','B1','B2','C1','C2']
FILLER = set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())
TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüßÀ-ÿ]+(?:[’'][A-Za-zÄÖÜäöüßÀ-ÿ]+)?")
TIME_RE = re.compile(r'\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]')


def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'item'


def title(path: Path) -> str:
    return re.sub(r'^\d+[\s._-]*', '', path.stem).strip()


def parse_lrc(path: Path):
    rows = []
    for raw in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        tags = list(TIME_RE.finditer(raw))
        text = TIME_RE.sub('', raw).strip()
        if not tags or not text:
            continue
        for t in tags:
            frac = t.group(3) or '0'
            sec = int(t.group(1))*60 + int(t.group(2)) + int(frac.ljust(3,'0'))/1000
            rows.append({'time': round(sec,3), 'text': text})
    rows.sort(key=lambda x:x['time'])
    for i, r in enumerate(rows):
        r['endTime'] = rows[i+1]['time'] if i+1 < len(rows) else round(r['time']+4.5,3)
    return rows


def pair_audio(lrc: Path):
    for p in lrc.parent.iterdir():
        if p.is_file() and p.suffix.lower() in {'.mp3','.m4a','.wav','.ogg','.aac'} and p.stem.lower() == lrc.stem.lower():
            return p
    return None


def call_ollama(model: str, prompt: str, timeout: int = 180, retries: int = 0):
    """Call Ollama without Qwen3's long thinking mode."""
    payload = {
        'model': model,
        'messages': [
            {'role':'system','content':'You are a careful German language editor for a vocabulary-learning app. Return ONLY valid JSON. Never use markdown. Do not explain your reasoning.'},
            {'role':'user','content':prompt}
        ],
        'stream': False,
        'think': False,
        'options': {'temperature': 0.05, 'num_ctx': 4096, 'num_predict': 2048}
    }
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode('utf-8'))
            text = ((data.get('message') or {}).get('content') or '').strip()
            text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.I).strip()
            try:
                return json.loads(text)
            except Exception:
                start, end = text.find('{'), text.rfind('}')
                if start >= 0 and end > start:
                    return json.loads(text[start:end+1])
                raise ValueError('Model did not return valid JSON')
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 5 * (attempt + 1)
                print(f'    Ollama call failed ({e}); retrying in {wait}s...', file=sys.stderr)
                time.sleep(wait)
    raise last_error


def review_lines(model, musical, song, lines, batch_size):
    cleaned = []
    for base in range(0, len(lines), batch_size):
        chunk = lines[base:base+batch_size]
        numbered = [{'i': base+i, 'time': x['time'], 'text': x['text']} for i,x in enumerate(chunk)]
        prompt = f'''Musical: {musical}\nSong: {song}\n\nReview these German LRC lyric lines.\nReturn exactly: {{"lines":[{{"i":0,"corrected":"...","english":"..."}}]}}\n\nRules:\n- Keep the timestamp index i exactly; timestamps are handled by the program.\n- Correct only clear spelling/transcription/OCR mistakes. Do NOT rewrite valid lyrics into different wording.\n- If a line is already correct, copy it unchanged.\n- Translate the ENTIRE corrected line into natural English.\n- Do not omit lines.\n- Do not provide reasoning or commentary.\n\nLines:\n{json.dumps(numbered, ensure_ascii=False)}'''
        ans = call_ollama(model, prompt)
        got = {int(x['i']): x for x in ans.get('lines',[]) if isinstance(x,dict) and str(x.get('i','')).isdigit()}
        for idx, x in enumerate(chunk, start=base):
            a = got.get(idx, {})
            cleaned.append({'index':idx,'time':x['time'],'endTime':x['endTime'],'text':str(a.get('corrected') or x['text']).strip(),'english':str(a.get('english') or '').strip()})
        print(f'    lyrics: {min(base+batch_size,len(lines))}/{len(lines)} lines', flush=True)
    return cleaned


def extract_vocab(model, musical, song, cleaned, batch_size):
    candidates = []
    seen = set()
    for i, line in enumerate(cleaned):
        for tok in TOKEN_RE.findall(line['text']):
            k = tok.lower()
            if len(k) < 2 or k in FILLER or k in seen:
                continue
            seen.add(k)
            candidates.append({'surface':tok,'line_index':i})

    vocab = []
    for base in range(0, len(candidates), batch_size):
        batch = candidates[base:base+batch_size]
        prompt = f'''Create learner vocabulary from these candidates from the German musical {musical}, song {song}.\nReturn exactly: {{"words":[{{"surface":"geht","lemma":"gehen","english":"to go","cefr":"A1","line_index":0}}]}}\n\nRules:\n- Only include useful German vocabulary a learner would reasonably study.\n- Exclude names, places, titles, stage directions, sound effects, interjections, filler, and grammatical noise.\n- Normalize inflected forms to the dictionary lemma where appropriate (ging -> gehen, Kindern -> Kind).\n- Keep compounds when they are meaningful vocabulary; do not split them into nonsense pieces.\n- English must be a concise, natural flashcard meaning in context.\n- CEFR must be A1/A2/B1/B2/C1/C2 based on real learner difficulty and commonness, NOT word length.\n- Common everyday words should generally be A1/A2; literary, idiomatic, rare or abstract words can be B2/C1/C2.\n- Do not force everything into B1.\n- Return only words that actually occur in the supplied lines.\n- Do not provide reasoning or commentary.\n\nCandidates:\n{json.dumps(batch, ensure_ascii=False)}'''
        ans = call_ollama(model, prompt)
        for w in ans.get('words',[]) if isinstance(ans.get('words',[]),list) else []:
            if not isinstance(w,dict):
                continue
            lemma = str(w.get('lemma') or w.get('surface') or '').strip()
            english = str(w.get('english') or '').strip()
            level = str(w.get('cefr') or '').upper().strip()
            li = w.get('line_index', 0)
            if not lemma or not english or level not in LEVELS or not str(li).isdigit():
                continue
            li = int(li)
            if li >= len(cleaned):
                continue
            vocab.append({'word':lemma,'translation':english,'level':level,'line':cleaned[li]['text'],'lineTranslation':cleaned[li]['english'],'line_index':li})
        print(f'    vocab: {min(base+batch_size,len(candidates))}/{len(candidates)} candidates', flush=True)
    return vocab


def write_clean_lrc(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    out=[]
    for x in lines:
        ms = int(round(x['time']*1000))
        mm, rem = divmod(ms, 60000)
        ss, milli = divmod(rem, 1000)
        out.append(f'[{mm:02d}:{ss:02d}.{milli:03d}]{x["text"]}')
    path.write_text('\n'.join(out)+'\n', encoding='utf-8')


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--music-dir', default='music')
    ap.add_argument('--out-dir', default='data/ai-reviewed')
    ap.add_argument('--lrc-out-dir', default='data/ai-reviewed/lrc')
    ap.add_argument('--model', default='qwen3:8b')
    ap.add_argument('--musical', help='Only process this Musical folder; recommended.')
    ap.add_argument('--song', help='Only process one song (filename or title).')
    ap.add_argument('--line-batch', type=int, default=12)
    ap.add_argument('--word-batch', type=int, default=35)
    ap.add_argument('--pause', type=float, default=0.2)
    args = ap.parse_args()

    music = Path(args.music_dir)
    outdir = Path(args.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    lrcout = Path(args.lrc_out_dir); lrcout.mkdir(parents=True, exist_ok=True)
    if not music.exists():
        raise SystemExit(f'Music directory not found: {music}')

    print('Checking Ollama/model (first load can take a few minutes)...', flush=True)
    try:
        call_ollama(args.model, 'Return exactly {"ok":true}', timeout=180, retries=0)
    except Exception as e:
        print(f'Ollama is not reachable: {e}', file=sys.stderr)
        raise SystemExit(1)

    dirs = [p for p in music.iterdir() if p.is_dir()]
    if args.musical:
        dirs = [p for p in dirs if p.name.lower() == args.musical.lower()]
        if not dirs:
            raise SystemExit(f'Musical not found: {args.musical}')
    else:
        print('No --musical supplied: processing all Musicals. For a MacBook, use --musical Elisabeth (or another one).')

    for md in sorted(dirs, key=lambda p:p.name.lower()):
        outpath = outdir/(slug(md.name)+'.json')
        payload = load_json(outpath, {'version':'','musical':md.name,'songs':[],'cards':[]})
        payload.setdefault('songs',[]); payload.setdefault('cards',[])
        song_done = {s.get('id'):s for s in payload['songs'] if isinstance(s,dict)}
        cards = {str(c.get('word','')).lower():c for c in payload['cards'] if isinstance(c,dict) and c.get('word')}

        lrcs = sorted([p for p in md.iterdir() if p.is_file() and p.suffix.lower()=='.lrc'], key=lambda p:p.name.lower())
        if args.song:
            q=args.song.lower()
            lrcs=[p for p in lrcs if p.name.lower()==q or p.stem.lower()==q or title(p).lower()==q]
        if not lrcs:
            print(f'[{md.name}] no matching LRC files')
            continue

        for lp in lrcs:
            sid=f'{slug(md.name)}::{slug(title(lp))}'
            existing_song=song_done.get(sid)
            if existing_song and existing_song.get('reviewed') is True:
                print(f'[{md.name}] SKIP already reviewed: {lp.name}')
                continue

            print(f'[{md.name}] REVIEW: {lp.name}', flush=True)
            original=parse_lrc(lp)
            cleaned=review_lines(args.model, md.name, title(lp), original, args.line_batch)
            vocab=extract_vocab(args.model, md.name, title(lp), cleaned, args.word_batch)
            audio=pair_audio(lp)
            clean_path=lrcout/md.name/lp.name
            write_clean_lrc(clean_path, cleaned)

            for w in vocab:
                key=w['word'].lower()
                cards[key] = {
                    **w,
                    'id':f'ai::{md.name}::{sid}::{key}',
                    'musical':md.name,
                    'show':md.name,
                    'song':title(lp),
                    'audioUrl':audio.as_posix() if audio else ''
                }

            song_done[sid] = {
                'id':sid,
                'title':title(lp),
                'lrc':lp.as_posix(),
                'cleanLrc':clean_path.as_posix(),
                'audio':audio.as_posix() if audio else '',
                'lineCount':len(cleaned),
                'vocabCount':len(vocab),
                'reviewed':True
            }
            payload['songs']=list(song_done.values())
            payload['cards']=list(cards.values())
            payload['version']=time.strftime('%Y%m%d-%H%M%S')
            outpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'    SAVED: {len(vocab)} words from this song; {len(cards)} total cards in {outpath}', flush=True)
            time.sleep(args.pause)

    print('DONE. Results are in data/ai-reviewed/ and corrected LRC files are in data/ai-reviewed/lrc/.')


if __name__ == '__main__':
    main()
