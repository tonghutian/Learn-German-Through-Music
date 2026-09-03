# Free local AI Musical Processor

This tool lets you prepare your built-in German musicals on your own Mac before publishing them. It uses Ollama locally, so there is no API key and no per-request cost. Your LRC text stays on your computer during AI processing.

## What it does

For every `.lrc` song under `music/<Musical>/` it:

1. Keeps every original timestamp and pairs it with the matching audio filename.
2. Uses a local Qwen model to fix obvious LRC transcription/spelling mistakes without changing timestamps.
3. Translates each complete lyric line to English.
4. Extracts useful German vocabulary instead of every token.
5. Converts inflected forms to a learner-friendly lemma where appropriate (`geht` → `gehen`).
6. Excludes names, places, stage directions, fillers and obvious non-vocabulary noise.
7. Assigns A1–C2 using the model's learner-difficulty judgment rather than word length.
8. Preserves already-edited translations/levels when an existing output JSON is present.
9. Writes one JSON file per Musical to `data/ai-reviewed/`.

## One-time Mac setup

Install Ollama from https://ollama.com/ . Then open Terminal and run:

```bash
ollama pull qwen3:8b
```

The current Ollama library lists `qwen3:8b` at about 5.2 GB and supports multilingual instruction/translation. `qwen3:4b` is about 2.5 GB if your Mac has less memory. See https://ollama.com/library/qwen3 .

## Run it

From the root of your cloned `Learn-German-Through-Music` repository:

```bash
python3 tools/ai_process_musicals.py --music-dir music --out-dir data/ai-reviewed --model qwen3:8b
```

The script processes one song at a time and smaller line batches, so a whole musical does not need to fit into one huge prompt.

## Review before publishing

Open the generated files in `data/ai-reviewed/` and spot-check a few songs and difficult words. The original LRC timestamps are preserved by the script; only the displayed lyric text and learning metadata are AI-edited.

## Publishing model

The public website should read the reviewed JSON as its canonical built-in content. Users never need Ollama, an API key, or an online translation request for the pre-made musicals.

Recommended workflow:

```text
music/Elisabeth/*.lrc + *.mp3
        ↓
local Ollama + qwen3:8b
        ↓
data/ai-reviewed/elisabeth.json
        ↓
spot-check / edit
        ↓
publish to data/musicals/elisabeth.json
        ↓
GitHub Pages
```
