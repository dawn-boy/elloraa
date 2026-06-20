# Copilot Instructions — AI Documentary Production Pipeline

## What This Is

An autonomous YouTube documentary production pipeline. Given a topic, it produces a fully composited video — narration, atmospheric stills, ambient music, and video assembly — using local open-source AI models with no human intervention between stages.

The format is "illustrated documentary": eerie, cinematic still images animated with motion, layered with voice narration and ambient music. The visual identity is grounded in painterly, atmospheric concept art — a normal world with something deeply wrong in it.

---

## Core Principles

**The manifest is the source of truth.** A single JSON file (the beats manifest) persists through every stage. Each stage reads from it and writes back. Nothing is assembled outside of it.

**The narration audio is the master clock.** Image duration, music length, and silence timing are all derived from TTS output — never decided upfront. This dependency only goes one way.

**The Director pass is the only reasoning pass.** One holistic LLM inference reads the full topic/script and fills every creative directive into the manifest. Downstream execution models (voice, image, music) consume pre-decided fields — they do not interpret intent.

**Schema does not change between stages.** The beat object shape is fixed. Fields are filled or mutated in place as the pipeline progresses.

---

## Pipeline

```
Topic
  │
  ▼
[Director Pass] ── LLM reads topic, writes full beats manifest
  │                 all directives decided here, durations pending
  ▼
[Voice] ── IndexTTS2 renders each narration beat
  │         beat.duration mutated with actual TTS output length
  ▼
[Image] ── Flux 1.D generates one still per narration/beat_only beat
  │         LoRA selected per beat based on director directive
  ▼
[Music] ── ACE-Step 1.5 generates one ambient track per segment
  │         duration derived from summed beat durations in segment
  ▼
[Compositing] ── FFmpeg assembles video from manifest
                  narration + music + animated stills → final video
```

---

## The Beats Manifest

The manifest is a JSON array of beat objects. The schema is fixed — every beat carries every field regardless of type. Fields with no value for a given type are `"none"`. Fields that will exist but aren't computed yet are `"pending"`.

### Beat Types

| Type | Description |
|---|---|
| `narration` | A voiced line with image and music underneath |
| `silence` | Dead air — no voice, no music, image holds |
| `beat_only` | Music alone for a fixed duration, no narration |
| `chapter_break` | Structural marker, optional title card |

### Schema

**Envelope (all types)**

| Field | Type | Notes |
|---|---|---|
| `id` | string | Unique beat identifier |
| `type` | enum | `narration` \| `silence` \| `beat_only` \| `chapter_break` |
| `chapter_id` | string | Which chapter this beat belongs to |
| `title` | string | `"none"` for most beats; chapter title for `chapter_break` |
| `note` | string | Director's human note — never passed to any model |
| `duration` | number \| `"pending"` \| `"none"` | Authored for non-narration types; `"pending"` on narration until TTS renders |

**`dialogue`** — string or `"none"`

**`voice`** — object or `"none"`

| Field | Type | Notes |
|---|---|---|
| `tone` | enum | `curious` \| `calm` \| `soft_laugh` |
| `intensity` | float 0–1 | Degree of tonal expression within the selected module |
| `pause_after` | float | Seconds of silence to pad after the line |

**`image`** — object or `"none"`

| Field | Type | Notes |
|---|---|---|
| `prompt_keywords` | string | Short tag-style keywords for the CLIP-L encoder |
| `prompt_description` | string | Full natural-language scene description for the T5 encoder |
| `negative_prompt` | string | What to avoid in generation |
| `lora` | string | Which LoRA to apply; `"none"` for no LoRA |
| `lora_strength` | float \| `"none"` | Applied strength of the LoRA |
| `aspect_ratio` | string \| `"none"` | Output aspect ratio |
| `seed` | int \| `"random"` \| `"none"` | Generation seed |
| `continue_previous` | enum | `"new"` = generate fresh; `"hold"` = reuse prior still; `"evolve"` = hold with subtle animation |

**`music`** — object or `"none"`

| Field | Type | Notes |
|---|---|---|
| `caption` | string | Full mood+texture description sent directly to ACE-Step |
| `ambience_cue` | string | Human-readable director note — not sent to any model |
| `duck_under_voice` | bool | Whether music should sidechain-duck under narration in compositing |
| `segment_id` | string | Beats sharing a segment ID share one ACE-Step generation |

---

## Stage 0 — Director Pass

The only stage with global context. An LLM reads the topic and writes every field of every beat into the manifest before any generation begins.

**Decides:**
- Beat sequence — which lines are `narration`, where `silence` or `beat_only` beats are placed
- Tone sequencing — ensures emotional variety across the video; must always start and end the narration sequence with the "curious" tone, using "calm" and "soft_laugh" sparingly in the middle. No more than ~3 consecutive curious beats without a calm break to prevent audience fatigue.
- Pause timing per narration beat
- Image directives — keyword and description fields appropriate for the intended LoRA's domain
- LoRA selection — if the dialogue content would fight a LoRA's trained aesthetic, the director assigns a different LoRA or `"none"` rather than forcing a mismatch
- Music captions per segment — must fully encode mood and atmosphere in text, since ACE-Step receives no other context about the narrative

**Does not decide:** actual TTS duration (unknown until rendered), image seeds (random unless locked), music duration (derived from beat durations).

All `narration` beats leave `duration: "pending"` after this stage.

---

## Stage 1 — Voice Generation (IndexTTS2)

IndexTTS2 is the primary voice model. It clones from a reference audio file and applies an emotion vector to control expressive tone.

**How tone works:** The pipeline maintains a set of pre-recorded reference clips — one per `tone` enum value (curious, calm, soft_laugh) located at `assets/voices/{tone}_tone.wav`. The voice stage dynamically resolves the correct reference file based on the beat's tone, which serves as the voice identity source for that line.

**Emotion vector:** IndexTTS2 accepts an 8-dimensional emotion vector: `[happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]`. The Director pass controls this indirectly through the `tone` and `intensity` fields; the voice stage maps those to concrete emotion vector values at runtime.

**Beat mutation at this stage:** After each narration beat renders, the output WAV's actual duration is measured and written back into `beat.duration` in the manifest. This is the only place durations originate for narration beats. All downstream stages (music length, video clip length, compositing timeline) depend on these mutated values.

Non-narration beats (`silence`, `beat_only`, `chapter_break`) are skipped entirely — their durations were authored by the Director.

---

## Stage 2 — Image Generation (Flux 1.D)

Flux 1.D is the image model. It uses a dual-encoder prompt structure: a short keyword field for CLIP-L and a long descriptive field for T5. Both fields come directly from the beat's `image` object.

**LoRA selection:** The pipeline supports multiple LoRAs for different aesthetic contexts. The Director determines which LoRA is appropriate per beat based on the content of the dialogue and scene. If a subject would fight a LoRA's trained domain rather than work with it, the director assigns `"none"` and Flux generates unassisted. LoRA routing is a manifest decision, not an image-time decision.

**Image reuse:** Beats where `continue_previous` is `"hold"` or `"evolve"` do not trigger a Flux call — they carry forward the previous beat's image. Generation only happens when `continue_previous == "new"`.

---

## Stage 3 — Music Generation (ACE-Step 1.5)

ACE-Step generates full ambient tracks from a text caption. Music is generated per **segment**, not per beat — beats sharing a `segment_id` are covered by one continuous generation.

**How beats inform music:** The segment's total duration is the sum of all beat durations within it (now resolved from Stage 1). The caption for the generation is derived from the `music.caption` fields of the beats in that segment — typically the dominant mood, or a synthesis across them if the segment has tonal variation.

**Silence and beat-only beats inform structure:** A `silence` beat within a segment signals that the generated music should have a natural low point or textural pull-back at that position. A `beat_only` beat signals the opposite — music takes the foreground with no competition. The Director writes `caption` and `ambience_cue` to reflect these moments, and the music generation should honor the resulting descriptors.

**Duck timing:** `duck_under_voice` is a compositing directive only. ACE-Step generates a continuous track; the ducking is applied in the assembly stage, not during generation.

---

## Stage 4 — Compositing (FFmpeg)

The manifest is fully resolved at this point — every beat has a real duration. FFmpeg assembles the video deterministically from these values.

**Assembly logic:**
- Each beat produces one video clip of exactly `beat.duration` seconds
- Narration beats: animated still + narration audio + ducked music
- Silence beats: held still + silence (no audio at all)
- Beat-only beats: held or evolving still + music only (no narration)
- Chapter breaks: title card treatment for `beat.duration` seconds

**Motion on stills:** Each still gets a slow Ken Burns (zoom/pan) motion applied over its duration. The direction and speed can vary per beat but the principle is constant — no static frames.

**Transitions:** Crossfade dissolves between beats. Not hard cuts.

**Audio mixing:** The narration track is the spine. Music sidechains under it wherever `duck_under_voice` is true — ducking is automatic based on narration energy, not manually keyframed per beat.

**The render is a pure read of the manifest.** No creative decisions happen here.

---

## Design Rules

1. **Schema is immutable mid-pipeline.** No field is added after Stage 0. If a new field is needed, it exists in the schema from the start.
2. **`"none"` and `"pending"` are semantically distinct.** `"none"` = nothing to generate, intentionally empty. `"pending"` = value will exist, not yet computed. Parsing code must treat them differently.
3. **Director is the only reasoning pass.** Execution models receive directives, not raw text. They do not make creative inferences.
4. **Music is per segment, not per beat.** A single ACE-Step call covers all beats in a segment. `duck_under_voice` is compositing metadata, not a generation parameter.
5. **`continue_previous != "new"` means no image generation.** No Flux call is made — the prior PNG is reused.
6. **Narration duration is always measured, never estimated.** The actual WAV length after TTS is the only valid source. No upfront estimates.
7. **Assembly is programmatic, not GUI-driven.** FFmpeg driven by the manifest is the compositing layer. GUI tools are reserved for optional manual passes (color grading) only.
