from pathlib import Path
import json, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA = Path("data/musicals")
CACHE = Path("data/translation_cache_lines.json")

def request_translation(text, timeout=12):
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({
        "client":"gtx","sl":"de","tl":"en","dt":"t","q":text
    })
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Learn-German-Through-Music/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8","replace"))
            return "".join(p[0] for p in (data[0] or []) if p and p[0]).strip()
        except Exception as e:
            last = e
            time.sleep(0.8 * (attempt + 1))
    return ""

def load_cache():
    try:
        x = json.loads(CACHE.read_text(encoding="utf-8"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def main():
    cache = load_cache()
    jobs = {}
    paths = sorted(DATA.glob("*.json"))
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for c in data.get("cards",[]):
            line = str(c.get("line") or "").strip()
            if line and not str(c.get("lineTranslation") or "").strip() and line not in cache:
                jobs[line] = line

    print("Missing unique lyric lines:", len(jobs), flush=True)
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(request_translation, line): line for line in jobs}
        for i, f in enumerate(as_completed(futures), 1):
            line = futures[f]
            try:
                t = f.result()
            except Exception:
                t = ""
            if t:
                cache[line] = t
            if i % 50 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
                print("Progress:", i, "/", len(futures), flush=True)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",",":")), encoding="utf-8")

    total = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for c in data.get("cards",[]):
            line = str(c.get("line") or "").strip()
            if line and not str(c.get("lineTranslation") or "").strip():
                t = cache.get(line,"").strip()
                if t:
                    c["lineTranslation"] = t
                    changed += 1
                    total += 1
        if changed:
            data["version"] = time.strftime("%Y%m%d-%H%M%S")
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
        print(path.name, "filled", changed, "cards", flush=True)
    print("Filled lyric-line translations:", total, flush=True)

if __name__ == "__main__":
    main()
