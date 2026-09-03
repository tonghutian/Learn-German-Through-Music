from pathlib import Path
import json, re, time, urllib.parse, urllib.request

DATA = Path('data/musicals')
INDEX = Path('index.html')
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
            req=urllib.request.Request(url, headers={'User-Agent':'Learn-German-Through-Music/1.0'})
        else:
            body=json.dumps(payload).encode('utf-8')
            req=urllib.request.Request(url, data=body, headers={'Content-Type':'application/json','User-Agent':'Learn-German-Through-Music/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8','replace'))
    except Exception:
        return None


def wiktionary(word):
    for title in [word, word.capitalize(), *[x.capitalize() for x in lemma_candidates(norm_word(word))[:4]]]:
        u='https://en.wiktionary.org/api/rest_v1/page/definition/'+urllib.parse.quote(title)
        data=http_json(u)
        if not data: continue
        entries=data.get('de') or data.get('en') or []
        if isinstance(entries,dict): entries=[entries]
        for entry in entries:
            for definition in entry.get('definitions',[]):
                g=clean_gloss(definition.get('definition',''))
                if g: return g
    return ''


def mymemory(text):
    q=urllib.parse.urlencode({'q':text,'langpair':'de|en'})
    data=http_json(MYMEMORY_URL+'?'+q)
    if not data: return ''
    t=((data.get('responseData') or {}).get('translatedText') or '').strip()
    if not t or re.search(r'MYMEMORY WARNING|QUERY LENGTH|INVALID',t,re.I): return ''
    return t


def libretranslate(text):
    data=http_json(LIBRE_URL, {'q':text,'source':'de','target':'en','format':'text'})
    return (data or {}).get('translatedText','').strip()


def get_zipf():
    try:
        from wordfreq import zipf_frequency
        return zipf_frequency
    except Exception:
        return None


def level_for(word, builtin, zipf):
    k=norm_word(word)
    if k in builtin and builtin[k].get('level'): return builtin[k]['level']
    if zipf:
        z=float(zipf(k,'de'))
        if z>=5.25: return 'A1'
        if z>=4.75: return 'A2'
        if z>=4.25: return 'B1'
        if z>=3.75: return 'B2'
        if z>=3.25: return 'C1'
        return 'C2'
    n=len(k)
    return 'A1' if n<=4 else 'A2' if n<=6 else 'B1' if n<=8 else 'B2' if n<=11 else 'C1' if n<=14 else 'C2'


def main():
    builtin=parse_builtin_dict()
    beolingus={}
    try:
        with urllib.request.urlopen(urllib.request.Request(BEOLINGUS_URL,headers={'User-Agent':'Learn-German-Through-Music/1.0'}),timeout=60) as r:
            beolingus=parse_beolingus(r.read().decode('utf-8','replace'))
        print('Beolingus entries:',len(beolingus))
    except Exception as e:
        print('Beolingus unavailable:',e)
    zipf=get_zipf()
    if zipf: print('wordfreq CEFR fallback enabled')
    total_words=total_lines=0
    for path in sorted(DATA.glob('*.json')):
        data=json.loads(path.read_text(encoding='utf-8'))
        cards=data.get('cards',[])
        unique_lines={}
        for c in cards:
            k=norm_word(c.get('word',''))
            if not k: continue
            translation=clean_gloss(c.get('translation',''))
            if not translation:
                hit=beolingus.get(k)
                if not hit:
                    for cand in lemma_candidates(k):
                        hit=beolingus.get(cand)
                        if hit: break
                if hit: translation=hit
                if not translation:
                    translation=wiktionary(c.get('word',''))
                if not translation:
                    translation=mymemory(c.get('word',''))
                if translation:
                    c['translation']=translation
                    total_words+=1
            else:
                c['translation']=translation
            # Always improve missing/old obviously placeholder levels.
            c['level']=level_for(c.get('word',''),builtin,zipf)
            if c.get('line') and not (c.get('lineTranslation') or '').strip():
                unique_lines.setdefault(c['line'].strip(),[]).append(c)
        for line, targets in unique_lines.items():
            en=libretranslate(line)
            if not en: en=mymemory(line)
            if en:
                for c in targets: c['lineTranslation']=en
                total_lines+=1
            time.sleep(0.08)
        # Refresh counts for the Library UI.
        counts={lv:0 for lv in LEVELS}
        for c in cards: counts[c.get('level') if c.get('level') in counts else 'B1']+=1
        data['levelCounts']=counts
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        print(path.name, 'cards',len(cards),'word translations',sum(bool(c.get('translation')) for c in cards),'line translations',sum(bool(c.get('lineTranslation')) for c in cards))
    print(f'Filled {total_words} missing word translations and {total_lines} unique lyric lines.')

if __name__=='__main__': main()
