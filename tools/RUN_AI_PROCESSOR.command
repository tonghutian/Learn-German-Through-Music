#!/bin/bash
set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"
echo "=============================================="
echo " Learn German Through Music — AI Processor"
echo "=============================================="
echo
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Install it from: https://ollama.com/"
  echo "Then run this file again."
  read -n 1 -s -r -p "Press any key to exit..."
  echo
  exit 1
fi

MODEL="qwen3:8b"
if ! ollama list >/dev/null 2>&1; then
  echo "Starting Ollama…"
  (ollama serve >/tmp/learn-german-ollama.log 2>&1 &)
  sleep 2
fi
if ! ollama list | awk 'NR>1 {print $1}' | grep -qx "$MODEL"; then
  echo "Downloading $MODEL (first time only)…"
  ollama pull "$MODEL"
fi

echo
python3 tools/ai_process_musicals.py --music-dir music --out-dir data/ai-reviewed --model "$MODEL"

echo
python3 - <<'PY'
from pathlib import Path
import json, shutil
src=Path('data/ai-reviewed'); dst=Path('data/musicals'); dst.mkdir(parents=True,exist_ok=True)
for p in src.glob('*.json'):
    data=json.loads(p.read_text(encoding='utf-8'))
    # Preserve only AI-reviewed canonical fields expected by the public site.
    cards=[]
    for c in data.get('cards',[]):
        cards.append(c)
    payload={"version":data.get("version",""),"musical":data.get("musical",p.stem),"cards":cards}
    (dst/p.name).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('Published AI-reviewed JSON into data/musicals/.')
PY

git add data/ai-reviewed data/musicals
git commit -m "Publish AI-reviewed German musical vocabulary" || true
git push

echo
echo "DONE. The reviewed vocabulary has been pushed to GitHub Pages."
read -n 1 -s -r -p "Press any key to close..."
echo
