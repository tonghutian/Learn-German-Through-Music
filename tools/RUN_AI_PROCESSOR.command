#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
echo
echo "Learn German Through Music — Local AI Musical Processor"
echo
echo "Uses Ollama locally. No paid API key is required."
echo
echo "IMPORTANT: this launcher processes ONE Musical at a time and saves after every song."

echo
echo "Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed."
  read -r -p "Press Enter to close..."
  exit 1
fi
if ! ollama list >/dev/null 2>&1; then
  echo "Ollama is not running. Open the Ollama app and run this file again."
  read -r -p "Press Enter to close..."
  exit 1
fi
MODEL="qwen3:8b"
if ! ollama show "$MODEL" >/dev/null 2>&1; then
  echo "Downloading $MODEL (~5 GB)..."
  ollama pull "$MODEL" || exit 1
fi

echo
echo "Available Musicals: Elisabeth / Mozart! / Rebecca / Tanz der Vampire"
read -r -p "Which Musical should I process? [Elisabeth]: " MUSICAL
MUSICAL="${MUSICAL:-Elisabeth}"

echo
echo "Starting: $MUSICAL"
echo "Small batches + checkpoint after every song."
python3 tools/ai_process_musicals.py \
  --music-dir music \
  --out-dir data/ai-reviewed \
  --lrc-out-dir data/ai-reviewed/lrc \
  --model "$MODEL" \
  --musical "$MUSICAL" \
  --line-batch 12 \
  --word-batch 35 \
  --pause 0.5

STATUS=$?
echo
if [ "$STATUS" -eq 0 ]; then
  echo "Finished. Results: data/ai-reviewed/"
else
  echo "Stopped with an error. Completed songs are already saved and will be skipped next time."
fi
read -r -p "Press Enter to close..."
exit "$STATUS"
