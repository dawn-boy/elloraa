# Project Status & AI Handoff Context

## Overview
This project is an autonomous YouTube documentary production pipeline. It takes a text script and produces a fully composited video using local AI models (LLMs, IndexTTS2, Flux 1.D, ACE-Step 1.5). 

The architectural single source of truth is the **Beats Manifest** (a strictly typed JSON file). Downstream stages read this manifest, execute their specific generation task, and write back (mutate) the manifest with results (like actual audio durations).

**Current Pipeline Priority:** Finishing the build up to **Stage 1 (Voice Generation)**.

---

## 🟢 Completed Work

### 1. Architecture & Structure
- Python environment initialized and managed strictly via `uv`.
- Project directory structure established (`src/`, `assets/`, `outputs/`, `documentations/`).
- `AGENTS.md` fully defines the pipeline rules, manifest schema, and constraints.

### 2. Data Models (`src/manifest.py`)
- Pydantic models created for the entire Beats Manifest (`Beat`, `VoiceDirective`, `ImageDirective`, `MusicDirective`).
- Strong typing enforces the schema (e.g., `duration` must be float or `"pending"`, specific string literals for `type` and `tone`).

### 3. Stage 0: Director Pass (`src/stages/stage0_director.py`)
- LLM integration drafted using OpenAI (GPT-4o) to ingest `assets/scripts/script.md` and output a strictly formatted JSON manifest.
- **Mocking:** To unblock Stage 1 development, a `mock_manifest_generator.py` was used to convert `script.md` into a fully valid 126-beat `outputs/manifests/manifest.json`. All `narration` beats currently have `duration: "pending"`.

### 4. Stage 1: Voice Engine (`src/stages/stage1_voice.py`)
- `VoiceEngine` class drafted to wrap **IndexTTS2**.
- Maps string-based tones (e.g., `"serious"`, `"calm"`) and `intensity` into IndexTTS2's required 8-dimensional emotion vector.
- Reference audio provided at `assets/voices/serious_tone.wav`.
- Setup scripts drafted to install dependencies (ffmpeg, git-lfs) and download HuggingFace checkpoints for IndexTTS2.

---

## 🟡 Next Steps (Immediate Action Required)

The immediate next task is to **hook up the Voice Engine to the Manifest**. 

The next AI agent should modify `src/stages/stage1_voice.py` (or create a pipeline orchestration script) to do the following:
1. **Load** the `outputs/manifests/manifest.json` using the Pydantic `BeatsManifest` class.
2. **Iterate** through all beats. For every beat where `type == "narration"`:
   - Extract `dialogue`, `voice.tone`, and `voice.intensity`.
   - Call `VoiceEngine.generate_narration(...)`.
   - Programmatically **measure the duration** of the resulting `.wav` file.
   - **Mutate** the `beat.duration` field from `"pending"` to the measured float value.
3. **Save** the updated manifest back to disk.

---

## 🧠 Crucial Context for AI Agents
- **Read `AGENTS.md` first.** It contains non-negotiable rules about how data flows.
- **Do not change the schema.** The shape of a `Beat` must remain uniform across all stages. 
- **Durations:** The narration audio is the master clock. You *cannot* estimate durations. You must generate the TTS audio first, measure the file, and then mutate the manifest.
- **Dependencies:** Use `uv run` or `uv add` for all Python tasks.
- **IndexTTS2 Docs:** Reference `documentations/indextts2.md` for proper formatting of the TTS inference arguments.