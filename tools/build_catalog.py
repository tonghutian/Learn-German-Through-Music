from pathlib import Path
import json
from datetime import datetime, timezone
import re

ROOT = Path('.')
MUSIC = ROOT / 'music'
OUT = ROOT / 'data' / 'catalog.json'
AUDIO_EXTS = {'.mp3', '.m4a', '.wav', '.ogg', '.aac'}

def slug(s: str) -> str:
    s = (s or '').lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s, flags=re.I).strip('-')
    return s or 'item'

def clean_title(name: str) -> str:
    s = Path(name).stem
    s = re.sub(r'^\d+[\s._-]*', '', s).strip()
    return s

def norm_stem(name: str) -> str:
    s = Path(name).stem.lower()
    s = re.sub(r'\.[^.]+$', '', s)
    s = s.replace('´', "'").replace('’', "'").replace('‘', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:
            previous = {}

    musicals = []
    if MUSIC.exists():
        for musical_dir in sorted([p for p in MUSIC.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            songs = []
            lrcs = {}
            audios = {}
            for p in musical_dir.iterdir():
                if not p.is_file():
                    continue
                if p.suffix.lower() == '.lrc':
                    lrcs[norm_stem(p.name)] = p
                elif p.suffix.lower() in AUDIO_EXTS:
                    audios[norm_stem(p.name)] = p
            for key, lrc in sorted(lrcs.items(), key=lambda kv: kv[0]):
                audio = audios.get(key)
                song_id = f"{slug(musical_dir.name)}::{slug(clean_title(lrc.name))}"
                songs.append({
                    'id': song_id,
                    'title': clean_title(lrc.name),
                    'musical': musical_dir.name,
                    'lrc': lrc.as_posix(),
                    'audio': audio.as_posix() if audio else '',
                })
            # Audio-only tracks are still listed for visibility, but have no lyric/timing data.
            for key, audio in sorted(audios.items(), key=lambda kv: kv[0]):
                if key in lrcs:
                    continue
                songs.append({
                    'id': f"{slug(musical_dir.name)}::{slug(clean_title(audio.name))}",
                    'title': clean_title(audio.name),
                    'musical': musical_dir.name,
                    'lrc': '',
                    'audio': audio.as_posix(),
                })
            musicals.append({
                'id': slug(musical_dir.name),
                'name': musical_dir.name,
                'description': '',
                'songs': songs,
            })

    cards = previous.get('cards', []) if isinstance(previous.get('cards', []), list) else []
    data = {
        'version': datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),
        'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'musicals': musicals,
        'cards': cards,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {OUT} with {len(musicals)} musicals and {sum(len(m['songs']) for m in musicals)} songs.")

if __name__ == '__main__':
    main()
