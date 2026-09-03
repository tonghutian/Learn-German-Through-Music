#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
echo
echo "Learn German Through Music — Local AI Musical Processor"
echo
echo "This uses Ollama on your Mac. No paid API key is required."
echo
echo "Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Install it from https://ollama.com/ and run this file again."
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
echo "Processing all musicals under music/..."
python3 tools/ai_process_musicals.py --music-dir music --out-dir data/ai-reviewed --model "$MODEL"
echo
echo "Finished. Review the files in data/ai-reviewed/ before publishing them."
read -r -p "Press Enter to close..."
