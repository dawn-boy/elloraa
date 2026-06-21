import os
import sys
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config import PATHS
from src.utils.llm_client import run_completion_with_lifecycle

SYSTEM_PROMPT_PASS1_PLANNER = """You are the Section Planner for an autonomous AI 
documentary production pipeline. Read the full script and divide it into logical 
sections. Do NOT write individual beats yet.

---

### WHAT MAKES A GOOD SECTION BOUNDARY
Cut a new section when ANY of these occur:
- Location or setting changes
- A significant time jump
- A tonal gear shift (the mood fundamentally changes)
- A revelation that reframes what came before
- A new character or object enters that drives the narrative forward

Do not cut mid-thought or mid-tension. Sections should feel like natural chapters.

---

### BEAT DENSITY RATIONALE
When deciding target_beat_count, reason through the excerpt's density:
- A single atmospheric moment (rain, a look, a sound) = 1–2 beats
- A character action or reaction = 1 beat
- A location with multiple layers to reveal = 3–4 beats
- A dramatic event (arrival, discovery, confrontation) = 4–6 beats
- A reflective passage = fewer beats, let them breathe
Be generous. Undershooting beat count is the most common failure.

---

### TONE VOCABULARY
emotional_tone_arc must use ONLY:
- `curious` — default documentary register. Discovery, unease, questioning, tension.
- `calm` — reflective, slow, weight settling in. Use sparingly.
- `soft_laugh` — dark irony only. Rare. Maximum once per section.

Do not use: serious, frustration, tense, sad, melancholic, or any other word.
Map everything to the three above.

---

### MUSIC SEGMENT PLANNING
For each section, decide where music changes. Mark the dominant music mood.
Music segments should change when the emotional register shifts significantly.
Include this in narrative_territory so Pass 2 knows where segment breaks land.

---

### OUTPUT FORMAT

<section id="1">
  <title>Section Title</title>
  <narrative_territory>
    What happens, what the emotional journey is, where music segments 
    should shift, and what the dominant visual motif is.
  </narrative_territory>
  <target_beat_count>10</target_beat_count>
  <emotional_tone_arc>curious -> calm -> curious</emotional_tone_arc>
  <dominant_music_mood>dark ambient drone, sparse, cold</dominant_music_mood>
  <contains_chapter_break>false</contains_chapter_break>
  <script_excerpt>
  ...verbatim text...
  </script_excerpt>
</section>

CRITICAL INSTRUCTION: You MUST output ONLY valid XML `<section>` tags.
DO NOT use Markdown formatting like `**` or `##`.
DO NOT output conversational text or explanations.
Your entire output must consist of `<section>...</section>` blocks and nothing else.
"""

SYSTEM_PROMPT_PASS2_BEAT_GEN = """You are the Beat Generator for an autonomous AI 
documentary production pipeline. You receive a Section Plan, a Script Excerpt, and 
the Last Beat from the previous section.

Generate EXACTLY the number of beats specified. Every significant moment gets a beat.

---

### TONE CONSTRAINT — HARD RULE
Voice Tone must be exactly one of: `curious`, `calm`, `soft_laugh`
Never use: frustration, curiosity, serious, tense, sad, melancholic, angry, neutral.
Mapping:
- frustration / tension / unease → `curious`
- curiosity / wonder / discovery → `curious`  
- serious / grave / ominous → `curious`
- reflective / sad / slow → `calm`
- dark irony → `soft_laugh`

Pacing: curious is the default. calm and soft_laugh are rare. Never more than 3 
consecutive curious beats without a break.

---

### NARRATION CRAFT
`dialogue` is the narrator's voice — never lifted from the script.
The script tells you WHAT HAPPENS. You write how a documentary narrator describes it.

Rules for good narration:
- Short lines. One idea per beat. 15–25 words is ideal.
- Write what the viewer sees, then what it means — not the other way around.
- End lines on a word with weight. Not a function word.
- Avoid adjective stacking. One strong image beats three descriptors.
- Write to be heard, not read. Say it aloud. If it sounds flat, rewrite it.

BAD: "The tropical rain fell in drenching sheets, hammering the corrugated roof 
      of the clinic building, roaring down the metal gutters."
GOOD: "The rain had been falling for three weeks. It showed no intention of stopping."

---

### IMAGE DESCRIPTION CRAFT
Every image description needs four elements: subject + environment + atmosphere + mood.
Be specific and cinematic. Never write a stage direction.
Negative prompts should always be populated — never write `none` for them.

Standard negatives to always include:
bright colors, photorealistic, sharp lighting, text, watermark, modern UI, crowd

BAD:  "Dr. Carter sitting at a desk, looking out a foggy window."
GOOD: "A lone figure hunched at a clinic desk, face turned toward a rain-blurred 
       window, the ocean beyond completely swallowed by fog. Muted teal and grey 
       palette. Overcast, diffused light. Painterly, cinematic stillness."

Visual pacing:
- `new` — new scene or significant subject change
- `evolve` — same scene, subtle shift in focus or atmosphere
- `hold` — image freezes (silence beats, very short moments)
Do not use `new` on every beat. Vary deliberately.

---

### MUSIC CAPTION DEPTH
ACE-Step receives the caption as its only context. It needs enough to generate 
the right atmosphere. Minimum six descriptors covering:
instrumentation + tempo feel + texture + percussion + intensity + emotional register

BAD:  "Soft ambient strings with a sense of nostalgia."
GOOD: "Dark ambient drone, low cello swell, no percussion, sparse high-frequency 
       texture like distant static, slow evolving pads, cold and desolate, 
       intensity level 3 of 10, building almost imperceptibly."

Silence beats always get: Music Caption: none, Music Segment ID: none

---

### BEAT SEQUENCING RULES
- Start by reading the Last Beat. Note: which image is on screen, which segment 
  is active, what tone just ended. Your first beat continues from that state.
- Group beats into music segments. Segments change when mood shifts significantly.
- Place silence beats deliberately — after a heavy revelation, before a new 
  subject is introduced. Not randomly.
- beat_only beats are for moments where music should carry the scene alone — 
  use when the script has no dialogue and the visual needs room to breathe.

---

### SELF-VALIDATION
Before outputting, check:
1. Every Voice Tone is exactly `curious`, `calm`, or `soft_laugh` — nothing else.
2. No dialogue is lifted verbatim from the script.
3. Every image description has subject + environment + atmosphere + mood.
4. Every music caption has at least 6 descriptors.
5. Negative prompts are never `none` on narration beats.
6. Beat count matches exactly what was requested.
7. Music segment IDs are consistent — beats in the same segment share the same ID.

---

### OUTPUT FORMAT

### Beat [id]
- Type: [type]
- Chapter ID: [chapter_id]
- Title: [title or "none"]
- Note: [director's note — never sent to any model]
- Dialogue: [original narrator voice or "none"]
- Voice Tone: [curious | calm | soft_laugh | "none"]
- Voice Intensity: [0.0–1.0 or "none"]
- Pause After: [seconds or "none"]
- Image Keywords: [short tag-style or "none"]
- Image Description: [subject + environment + atmosphere + mood or "none"]
- Image Negative: [what to avoid — never "none" on narration beats]
- Image LoRA: [lora-name or "none"]
- Image LoRA Strength: [float or "none"]
- Image Aspect Ratio: [16:9 or "none"]
- Image Seed: [integer or "none"]
- Image Continue: [new | hold | evolve | "none"]
- Music Caption: [6+ descriptor ACE-Step caption or "none"]
- Music Cue: [human note, not sent to model or "none"]
- Music Duck: [true | false | "none"]
- Music Segment ID: [segment_id or "none"]
"""

def parse_sections(xml_text: str):
    sections = []
    
    # 1. Try to parse as XML
    pattern = r'<section([^>]*)>(.*?)</section>'
    matches = list(re.finditer(pattern, xml_text, re.DOTALL | re.IGNORECASE))
    
    if matches:
        for i, m in enumerate(matches):
            attrs = m.group(1)
            content = m.group(2)
            
            id_match = re.search(r'id=["\']?([^"\'>\s]+)', attrs, re.IGNORECASE)
            sec_id = id_match.group(1) if id_match else str(i + 1)
            
            title = re.search(r'<title>(.*?)</title>', content, re.DOTALL | re.IGNORECASE)
            beats = re.search(r'<target_beat_count>(.*?)</target_beat_count>', content, re.DOTALL | re.IGNORECASE)
            excerpt = re.search(r'<script_excerpt>(.*?)</script_excerpt>', content, re.DOTALL | re.IGNORECASE)
            
            raw_beats = beats.group(1).strip() if beats else "10"
            
            sections.append({
                "id": sec_id,
                "title": title.group(1).strip() if title else f"Section {sec_id}",
                "target_beat_count": raw_beats,
                "excerpt": excerpt.group(1).strip() if excerpt else "",
                "raw": m.group(0)
            })
        return sections
        
    # 2. Markdown Fallback (DeepSeek R1 sometimes ignores XML instructions)
    parts = re.split(r'(?i)###\s*Section\s*(\d+)', xml_text)
    if len(parts) > 1:
        # parts[0] is preamble. parts[1] is ID 1, parts[2] is content 1, parts[3] is ID 2, etc.
        for i in range(1, len(parts), 2):
            sec_id = parts[i].strip()
            content = parts[i+1]
            
            title_match = re.search(r'\*\*Title:\*\*\s*(.*?)\n', content, re.IGNORECASE)
            beats_match = re.search(r'\*\*Target Beat Count:\*\*\s*(\d+)', content, re.IGNORECASE)
            excerpt_match = re.search(r'\*\*Script Excerpt:\*\*\s*(.*?)(?=\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
            
            title = title_match.group(1).strip() if title_match else f"Section {sec_id}"
            raw_beats = beats_match.group(1).strip() if beats_match else "10"
            excerpt = excerpt_match.group(1).strip() if excerpt_match else ""
            
            sections.append({
                "id": sec_id,
                "title": title,
                "target_beat_count": raw_beats,
                "excerpt": excerpt,
                "raw": f"### Section {sec_id}\n{content}"
            })
            
    return sections

def generate_plan(script_path: str, output_name: str = "director_plan.md", local: bool = False) -> str:
    with open(script_path, "r") as f:
        script_text = f.read()

    print("="*60)
    print(">>> PASS 1: SECTION PLANNER")
    print("="*60)
    
    model_name = "repos/DeepSeek-R1-Distill-Qwen-32B-FP8" if local else "gpt-4o"
    
    messages_pass1 = [
        {"role": "system", "content": SYSTEM_PROMPT_PASS1_PLANNER},
        {"role": "user", "content": f"Here is the full script to process:\n\n{script_text}"}
    ]
    
    sections_xml = run_completion_with_lifecycle(
        model_name=model_name,
        messages=messages_pass1,
        temperature=0.6,
        local=local,
        keep_alive=True
    )
    
    sections = parse_sections(sections_xml)
    if not sections:
        print("Warning: Could not parse sections from Pass 1. Proceeding with raw output as a single section.")
        print(f"RAW XML OUTPUT FROM PASS 1:\n{'-'*40}\n{sections_xml}\n{'-'*40}")
        sections = [{"id": "1", "title": "Full Script", "target_beat_count": "20", "excerpt": script_text, "raw": sections_xml}]
    
    print(f"Pass 1 generated {len(sections)} sections.")
    
    print("="*60)
    print(">>> PASS 2: BEAT GENERATOR (LOOPED)")
    print("="*60)
    
    os.makedirs(PATHS["manifests_dir"], exist_ok=True)
    out_path = os.path.join(PATHS["manifests_dir"], output_name)
    
    # Clear the file before starting the loop
    with open(out_path, "w") as f:
        f.write("")
    
    last_beat = "None (This is the first section)"
    beat_id_counter = 1
    
    for i, sec in enumerate(sections):
        print(f"Generating beats for Section {sec['id']}: {sec['title']} (Target: {sec['target_beat_count']} beats)")
        
        user_prompt = f"""### Section Plan Entry:
{sec['raw']}

### Last Beat From Previous Section:
{last_beat}

### Instruction:
Generate EXACTLY {sec['target_beat_count']} beats for this section.
Use continuous global beat IDs (e.g. if the last beat was 12, start with 13).
DO NOT wrap the output in markdown code blocks. Just output the beats.
"""
        messages_pass2 = [
            {"role": "system", "content": SYSTEM_PROMPT_PASS2_BEAT_GEN},
            {"role": "user", "content": user_prompt}
        ]
        
        is_last_section = (i == len(sections) - 1)
        section_beats = run_completion_with_lifecycle(
            model_name=model_name,
            messages=messages_pass2,
            temperature=0.6,
            local=local,
            keep_alive=not is_last_section
        )
        
        # Write to the file instantly!
        with open(out_path, "a") as f:
            f.write(f"\n<!-- SECTION {sec['id']} -->\n")
            f.write(section_beats + "\n")
            f.flush()
        
        print(f"Section {sec['id']} written to {out_path}!")
        
        # Extract the last beat to pass to the next section
        beat_blocks = section_beats.split("### Beat")
        if len(beat_blocks) > 1:
            last_beat = "### Beat" + beat_blocks[-1]
            
    print(f"\nDirector plan fully saved to {out_path}")
    return out_path

if __name__ == "__main__":
    script_p = os.path.join(PATHS["scripts_dir"], "script.md")
    use_local = "--local" in sys.argv
    generate_plan(script_p, local=use_local)
