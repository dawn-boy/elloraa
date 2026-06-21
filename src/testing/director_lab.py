"""
director_lab.py — Director Stage testing harness with per-section looping.

Architecture:
  Pass 1 (Section Mapper):     One call. Full script in. Sections + markers out.
  Script Slicer:               Python extracts real verbatim text between markers.
  Pass 2 (Story & Imagery):    One call per section. Free prose narration out.
  Pass 3 (Beat Formatter):     One call per section. Structured beats out.

Outputs are saved per-section and also concatenated into final files.
This replaces the old linear prompt_lab.py chain which fed everything into
a single Pass 2 generation — causing attention drift and section collapse.

Usage:
    uv run python src/testing/director_lab.py
    uv run python src/testing/director_lab.py --config src/testing/director_lab_config.json
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.llm_client import run_completion_with_lifecycle
from src.testing.script_slicer import slice_sections, format_sections_summary


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "model_name": "repos/DeepSeek-R1-Distill-Qwen-32B-FP8",
    "temperature": 0.6,
    "script_path": "assets/scripts/script.md",
    "pass1_system_prompt": "src/testing/prompts/sys_pass1.txt",
    "pass2_system_prompt": "src/testing/prompts/sys_pass2.txt",
    "pass3_system_prompt": "src/testing/prompts/sys_pass3.txt",
    "output_dir": "src/testing/outputs",
    "experiment_id": None   # auto-generated if None
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def abs_path(rel: str) -> str:
    return os.path.join(PROJECT_ROOT, rel)


def read_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def strip_think_block(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from model output."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def call_model(model_name: str, sys_prompt: str, user_prompt: str,
               temperature: float, label: str) -> str:
    print(f"\n  [model] Running {label}...")
    output = run_completion_with_lifecycle(
        model_name=model_name,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=temperature,
        local=True,
        keep_alive=True
    )
    print(f"  [model] {label} complete. ({len(output)} chars raw)")
    return output


def extract_last_beat_context(pass3_output: str, section_id: str) -> str:
    """
    Extract the last Beat block from a Pass 3 output to use as
    continuity context for the next section.
    Returns a short prose summary of the last beat's key fields.
    """
    # Find all beat blocks
    beat_blocks = re.findall(r'(### Beat \d+.*?)(?=### Beat \d+|\Z)', pass3_output, re.DOTALL)
    if not beat_blocks:
        return "No previous beat context available."

    last = beat_blocks[-1].strip()

    # Extract key fields for the handoff note
    def get_field(text, field):
        m = re.search(rf'^- {field}:\s*(.+)$', text, re.MULTILINE)
        return m.group(1).strip() if m else "unknown"

    tone       = get_field(last, "Voice Tone")
    image_desc = get_field(last, "Image Description")
    seg_id     = get_field(last, "Music Segment ID")
    continue_p = get_field(last, "Image Continue")
    chapter_id = get_field(last, "Chapter ID")

    return (
        f"--- PREVIOUS SECTION LAST BEAT (Section {section_id}) ---\n"
        f"Voice Tone: {tone}\n"
        f"Image on screen: {image_desc}\n"
        f"Music Segment ID: {seg_id}\n"
        f"Image Continue was: {continue_p}\n"
        f"Chapter ID: {chapter_id}\n"
        f"---\n"
        f"Use the above to decide Image Continue for your first beat and to\n"
        f"continue the segment_id numbering (do not restart from 1)."
    )


def build_pass2_user_prompt(section: dict, last_beat_context: str) -> str:
    """Build the user message for Pass 2 (Story & Imagery) for one section."""
    return f"""{last_beat_context}

---

## Section {section['id']}: {section['title']}

Narrative territory (what this section covers and why it matters):
{section['narrative_territory']}

Suggested beat count: {section['suggested_beat_count']} beats
(This is a density guide. Let the scene decide the exact count within this range.)

Contains chapter break: {'Yes' if section['contains_chapter_break'] else 'No'}

---

## Source Script Excerpt

The following is the exact source text this section covers. Use it as
reference for what happens — do NOT lift language from it directly.
Transform it into documentary narration.

{section['script_excerpt']}
"""


def build_pass3_user_prompt(section: dict, pass2_output: str,
                             last_beat_context: str, global_beat_offset: int,
                             chapter_id: int) -> str:
    """Build the user message for Pass 3 (Beat Formatter) for one section."""
    # Strip think block from Pass 2 output — Pass 3 only needs the story content
    clean_story = strip_think_block(pass2_output)

    return f"""{last_beat_context}

---

## Formatting Instructions for Section {section['id']}: {section['title']}

Chapter ID for all beats in this section: {chapter_id}
{'This section contains a chapter break — add one chapter_break beat at the start.' if section['contains_chapter_break'] else 'No chapter break in this section.'}
Beat IDs: start from {global_beat_offset + 1} and number sequentially.

---

## Story Draft (Pass 2 output — translate this, do NOT rewrite it)

{clean_story}
"""


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_director_lab(config: dict):
    model_name    = config["model_name"]
    temperature   = config["temperature"]
    script_path   = abs_path(config["script_path"])
    pass1_prompt  = read_file(abs_path(config["pass1_system_prompt"]))
    pass2_prompt  = read_file(abs_path(config["pass2_system_prompt"]))
    pass3_prompt  = read_file(abs_path(config["pass3_system_prompt"]))
    output_dir    = abs_path(config["output_dir"])
    exp_id        = config["experiment_id"] or datetime.now().strftime("dir_%Y%m%d_%H%M%S")

    exp_dir = os.path.join(output_dir, exp_id)
    os.makedirs(exp_dir, exist_ok=True)

    print("\n" + "="*65)
    print("  DIRECTOR LAB — Per-Section Loop")
    print("="*65)
    print(f"  Model:      {model_name}")
    print(f"  Experiment: {exp_id}")
    print(f"  Script:     {script_path}")
    print(f"  Output dir: {exp_dir}")
    print("="*65)

    # ------------------------------------------------------------------
    # PASS 1 — Section Mapper (one call, full script in)
    # ------------------------------------------------------------------
    print("\n[PASS 1] Section Mapper — mapping full script into sections...")
    script_text = read_file(script_path)

    pass1_raw = call_model(
        model_name, pass1_prompt, script_text, temperature,
        label="Pass 1 (Section Mapper)"
    )

    pass1_path = os.path.join(exp_dir, "pass1_sections.xml")
    write_file(pass1_path, pass1_raw)
    print(f"  Saved: {pass1_path}")

    # Strip think block before slicing (markers are in the XML, not the think block)
    pass1_clean = strip_think_block(pass1_raw)

    # ------------------------------------------------------------------
    # SCRIPT SLICER — extract real text between markers
    # ------------------------------------------------------------------
    print("\n[SLICER] Extracting script excerpts from markers...")
    try:
        sections = slice_sections(pass1_clean, script_path)
    except ValueError as e:
        print(f"\n[ERROR] Script slicer failed:\n{e}")
        print("\nPass 1 raw output was saved. Fix the markers and re-run.")
        return

    print(f"  Found {len(sections)} sections:")
    print(format_sections_summary(sections))

    # Save the enriched section plan as JSON for inspection
    sections_json_path = os.path.join(exp_dir, "sections_plan.json")
    write_file(sections_json_path, json.dumps(sections, indent=2, ensure_ascii=False))
    print(f"  Saved: {sections_json_path}")

    # ------------------------------------------------------------------
    # PER-SECTION LOOP — Pass 2 → Pass 3 for each section
    # ------------------------------------------------------------------
    all_beats_output   = []   # collected Pass 3 outputs per section
    all_story_output   = []   # collected Pass 2 outputs per section
    last_beat_context  = "This is the first section — no previous beat context."
    global_beat_offset = 0    # tracks how many beats have been emitted so far
    chapter_id         = 1    # tracks current chapter

    for section in sections:
        sec_id = section['id']
        print(f"\n{'─'*65}")
        print(f"  SECTION {sec_id}: {section['title']}")
        print(f"  Beats: {section['suggested_beat_count']} | "
              f"Chapter break: {section['contains_chapter_break']} | "
              f"Excerpt: {len(section['script_excerpt'])} chars")
        print(f"{'─'*65}")

        # ---- PASS 2: Story & Imagery ----
        p2_user = build_pass2_user_prompt(section, last_beat_context)
        p2_raw = call_model(
            model_name, pass2_prompt, p2_user, temperature,
            label=f"Pass 2 (Story) — Section {sec_id}"
        )
        p2_path = os.path.join(exp_dir, f"sec{sec_id}_pass2_story.md")
        write_file(p2_path, p2_raw)
        print(f"  Saved: {p2_path}")
        all_story_output.append(f"<!-- SECTION {sec_id}: {section['title']} -->\n\n{p2_raw}")

        # ---- PASS 3: Beat Formatter ----
        # Increment chapter_id if this section has a chapter break
        if section['contains_chapter_break']:
            chapter_id += 1

        p3_user = build_pass3_user_prompt(
            section, p2_raw, last_beat_context, global_beat_offset, chapter_id
        )
        p3_raw = call_model(
            model_name, pass3_prompt, p3_user, temperature,
            label=f"Pass 3 (Formatter) — Section {sec_id}"
        )
        p3_path = os.path.join(exp_dir, f"sec{sec_id}_pass3_beats.md")
        write_file(p3_path, p3_raw)
        print(f"  Saved: {p3_path}")
        all_beats_output.append(f"<!-- SECTION {sec_id}: {section['title']} -->\n\n{p3_raw}")

        # Count beats produced in this section to update the global offset
        beat_count = len(re.findall(r'^### Beat \d+', p3_raw, re.MULTILINE))
        global_beat_offset += beat_count
        print(f"  Beats produced: {beat_count} | Running total: {global_beat_offset}")

        # Extract last beat context for the next section
        last_beat_context = extract_last_beat_context(p3_raw, sec_id)

    # ------------------------------------------------------------------
    # FINAL OUTPUTS — concatenate all sections
    # ------------------------------------------------------------------
    print(f"\n{'='*65}")
    print("  CONCATENATING FINAL OUTPUTS")
    print(f"{'='*65}")

    final_story_path = os.path.join(exp_dir, "final_story_all_sections.md")
    write_file(final_story_path, "\n\n---\n\n".join(all_story_output))
    print(f"  Story (all sections): {final_story_path}")

    final_beats_path = os.path.join(exp_dir, "final_beats_all_sections.md")
    write_file(final_beats_path, "\n\n---\n\n".join(all_beats_output))
    print(f"  Beats (all sections): {final_beats_path}")

    print(f"\n  Total beats emitted: {global_beat_offset}")
    print(f"  Experiment ID: {exp_id}")
    print("\n  vLLM server is still running. Update config and re-run for next experiment.")
    print("="*65 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Director Lab — per-section loop for documentary pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON config file. Defaults to built-in DEFAULT_CONFIG."
    )
    args = parser.parse_args()

    config = dict(DEFAULT_CONFIG)

    if args.config:
        config_path = os.path.join(PROJECT_ROOT, args.config)
        with open(config_path, 'r') as f:
            override = json.load(f)
        config.update(override)

    run_director_lab(config)


if __name__ == "__main__":
    main()
