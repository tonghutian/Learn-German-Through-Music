from pathlib import Path
import json, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA = Path('data/musicals')
INDEX = Path('index.html')
CACHE = Path('data/translation_cache.json')
BEOLINGUS_URL = 'https://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt'
MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
LIBRE_URL = 'https://translate.argosopentech.com/translate'
LEVELS = ['A1','A2','B1','B2','C1','C2']
META_RE = re.compile(r'\b(imperative|participle|infinitive|subjunctive|indicative|conjugation|declension|genitive|dative|accusative|nominative|plural form|singular form|first-person|second-person|third-person)\b', re.I)
COMMON = set('aber alle als am an auch auf aus bei bin bis das dass dein deine dem den der des die dir doch du ein eine er es für ganz hat haben ich im in ist ja kann kein mit nach nicht nur oder sie sind so und vom von vor was wenn wie wir zu zum zur'.split())


def norm_word(s):
    return re.sub(r"[^A-Za-zÄÖÜäöüßÀ-ÿ'-]", '', str(s or '')).strip("'-").lower()


def clean_gloss(s):
    if not s: return ''
    s = re.sub(r'<[^>]+>', ' ', str(s))
    s = re.sub(r'\{[^}]+\}', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.split(r'[;|]', s)[0].strip()
    if not s or len(s) > 90 or META_RE.search(s): return ''
    if s.lower().startswith(('form of ', 'see ', 'alternative ', 'abbreviation ')): return ''
    return s


def lemma_candidates(key):
    out=[]
    def add(x):
        if x and x != key and len(x) >= 2 and x not in out: out.append(x)
    if key.endswith('es') and len(key)>4: add(key[:-2]); add(key[:-1])
    if key.endswith('em') and len(key)>4: add(key[:-2])
    if key.endswith('er') and len(key)>4: add(key[:-2]); add(key[:-1])
    if key.endswith('en') and len(key)>4: add(key[:-2]); add(key[:-1])
    if key.endswith('s') and len(key)>3 and not key.endswith(('ss','us','is')): add(key[:-1])
    if key.endswith('n') and len(key)>3 and not key.endswith(('en','nn')): add(key[:-1])
    if key.endswith('e') and len(key)>3: add(key[:-1]); add(key[:-1]+'en')
    if key.endswith('t') and len(key)>3: add(key[:-1]+'en')
    return out


def parse_builtin_dict():
    if not INDEX.exists(): return {}
    text = INDEX.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'const\s+GERMAN_DICT\s*=\s*\{([\s\S]*?)\n\s*\};', text)
    if not m: return {}
    d={}
    pat = re.compile(r'"([^"]+)"\s*:\s*\{\s*en:"([^"]*)"\s*,\s*level:(\d+)\s*\}')
    for word,en,lv in pat.findall(m.group(1)):
        i=int(lv)
        d[word.lower()]={'en':clean_gloss(en),'level':LEVELS[i-1] if 1<=i<=6 else None}
    return {k:v for k,v in d.items() if v['en']}


def parse_beolingus(text):
    d={}
    for line in text.splitlines():
        if not line or line[0] in '#%': continue
        parts=line.split('::')
        if len(parts)<2: continue
        de_groups=[x.strip() for x in parts[0].split('|') if x.strip()]
        en_groups=[x.strip() for x in '::'.join(parts[1:]).split('|') if x.strip()]
        if not en_groups: continue
        for idx, de_group in enumerate(de_groups):
            raw_en=en_groups[idx] if idx<len(en_groups) else en_groups[0]
            en=clean_gloss(raw_en)
            if not en: continue
            for alt in de_group.split(';'):
                alt=re.sub(r'\{[^}]*\}|\[[^\]]*\]|\([^)]*\)',' ',alt).strip()
                if not alt or ' ' in alt: continue
                k=norm_word(alt)
                if 2<=len(k)<=40 and k not in d: d[k]=en
    return d


def http_json(url, payload=None, timeout=15):
    try:
        if payload is None:
            req=urllib.request.Request(url,headers={'User-Agent':'Learn-German-Through-Music/1.0'})
        else:
            req=urllib.request.Request(url,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json','User-Agent':'Learn-German-Through-Music/1.0'})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8','replace'))
    except Exception:
        return None


def wiktionary(word):
    titles=[word,word.capitalize(),*[x.capitalize() for x in lemma_candidates(norm_word(word))[:4]]]
    for title in titles:
        data=http_json('https://en.wiktionary.org/api/rest_v1/page/definition/'+urllib.parse.quote(title),timeout=12)
        if not data: continue
        entries=data.get('de') or data.get('en') or []
        if isinstance(entries,dict): entries=[entries]
        for entry in entries:
            for definition in entry.get('definitions',[]):
                g=clean_gloss(definition.get('definition',''))
                if g: return g
    return ''


def mymemory(text):
    data=http_json(MYMEMORY_URL+'?'+urllib.parse.urlencode({'q':text,'langpair':'de|en'}),timeout=12)
    t=((data or {}).get('responseData') or {}).get('translatedText') or ''
    t=t.strip()
    if not t or re.search(r'MYMEMORY WARNING|QUERY LENGTH|INVALID',t,re.I): return ''
    return clean_gloss(t) or t[:90]


def libretranslate(text):
    data=http_json(LIBRE_URL,{'q':text,'source':'de','target':'en','format':'text'},timeout=20)
    t=((data or {}).get('translatedText') or '').strip()
    return t[:400]


def load_cache():
    try: return json.loads(CACHE.read_text(encoding='utf-8'))
    except Exception: return {'words':{},'lines':{}}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True,exist_ok=True)
    CACHE.write_text(json.dumps(cache,ensure_ascii=False,separators=(',',':')),encoding='utf-8')


def level_for(word,builtin,zipf):
    k=norm_word(word)
    hit=builtin.get(k)
    if hit and hit.get('level'): return hit['level']
    if zipf:
        z=float(zipf(k,'de'))
        # Frequency-based CEFR estimate: common words map to lower levels; rarer words to higher levels.
        if z>=5.60: return 'A1'
        if z>=5.05: return 'A2'
        if z>=4.45: return 'B1'
        if z>=3.90: return 'B2'
        if z>=3.35: return 'C1'
        return 'C2'
    return 'A1' if len(k)<=4 else 'A2' if len(k)<=6 else 'B1' if len(k)<=8 else 'B2' if len(k)<=11 else 'C1' if len(k)<=14 else 'C2'


def translate_one(word,builtin,beolingus,cache):
    key=norm_word(word)
    if not key: return ''
    cached=cache['words'].get(key,'')
    if cached: return cached
    hit=builtin.get(key)
    if hit and hit.get('en'):
        cache['words'][key]=hit['en']; return hit['en']
    hit=beolingus.get(key)
    if not hit:
        for cand in lemma_candidates(key):
            hit=beolingus.get(cand)
            if hit: break
    if hit:
        cache['words'][key]=hit; return hit
    result=wiktionary(word)
    if not result: result=mymemory(word)
    if result: cache['words'][key]=result
    return result


def translate_line_one(line,cache):
    key=line.strip()
    if not key: return ''
    cached=cache['lines'].get(key,'')
    if cached: return cached
    result=libretranslate(key)
    if not result: result=mymemory(key)
    if result: cache['lines'][key]=result
    return result


def main():
    builtin=parse_builtin_dict(); cache=load_cache(); beolingus={}
    try:
        req=urllib.request.Request(BEOLINGUS_URL,headers={'User-Agent':'Learn-German-Through-Music/1.0'})
        with urllib.request.urlopen(req,timeout=60) as r: beolingus=parse_beolingus(r.read().decode('utf-8','replace'))
        print('Beolingus entries:',len(beolingus))
    except Exception as e: print('Beolingus unavailable:',e)
    try:
        from wordfreq import zipf_frequency
        zipf=zipf_frequency
        print('wordfreq CEFR fallback enabled')
    except Exception:
        zipf=None
        print('wordfreq unavailable; using conservative length fallback')

    word_jobs={}; line_jobs={}
    paths=sorted(DATA.glob('*.json'))
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8'))
        cards=data.get('cards',[])
        for c in cards:
            if c.get('translation'): continue
            w=c.get('word','')
            key=norm_word(w)
            if key and key not in cache['words']: word_jobs[key]=w
        for c in cards:
            line=(c.get('line') or '').strip()
            if line and not (c.get('lineTranslation') or '').strip() and line not in cache['lines']:
                line_jobs[line]=line

    print('Missing unique words:',len(word_jobs),'· missing unique lyric lines:',len(line_jobs))

    # Do the slow online fallbacks concurrently, while keeping the large dictionaries local.
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures={ex.submit(translate_one,w,builtin,beolingus,cache):key for key,w in word_jobs.items()}
        for i,f in enumerate(as_completed(futures),1):
            try: f.result()
            except Exception: pass
            if i%100==0: print('Word translation fallback progress:',i,'/',len(futures)); save_cache(cache)
    save_cache(cache)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures={ex.submit(translate_line_one,line,cache):line for line in line_jobs.values()}
        for i,f in enumerate(as_completed(futures),1):
            try: f.result()
            except Exception: pass
            if i%25==0: print('Lyric line progress:',i,'/',len(futures)); save_cache(cache)
    save_cache(cache)

    total_filled=0; total_lines=0
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8')); cards=data.get('cards',[])
        for c in cards:
            k=norm_word(c.get('word',''))
            if not c.get('translation') and k:
                en=cache['words'].get(k,'')
                if en: c['translation']=en; total_filled+=1
            c['level']=level_for(c.get('word',''),builtin,zipf)
            line=(c.get('line') or '').strip()
            if line and not (c.get('lineTranslation') or '').strip():
                en=cache['lines'].get(line,'')
                if en: c['lineTranslation']=en; total_lines+=1
        counts={lv:0 for lv in LEVELS}
        for c in cards: counts[c.get('level') if c.get('level') in counts else 'B1']+=1
        data['levelCounts']=counts
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        print(path.name,'translated',sum(bool(c.get('translation')) for c in cards),'/',len(cards),'lines',sum(bool(c.get('lineTranslation')) for c in cards))
    print('Filled',total_filled,'word translations and',total_lines,'lyric-line translations.')

if __name__=='__main__': main()
