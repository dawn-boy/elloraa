import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from openai import OpenAI
from src.config import PATHS
from src.manifest import BeatsManifest
from src.utils.llm_client import run_completion_with_lifecycle

SYSTEM_PROMPT_FORMATTER = """You are the Formatter/Compiler for an autonomous AI documentary production pipeline.
Your job is to read a structured Markdown production plan and compile it into a strictly formatted JSON manifest.

The output will be parsed into this Pydantic schema:

```python
class VoiceDirective(BaseModel):
    tone: Literal["curious", "calm", "soft_laugh"]
    intensity: float # 0.0 to 1.0
    pause_after: float

class ImageDirective(BaseModel):
    prompt_keywords: str
    prompt_description: str
    negative_prompt: str
    lora: str # use "none" if no lora
    lora_strength: Union[float, Literal["none"]]
    aspect_ratio: Union[str, Literal["none"]]
    seed: Union[int, Literal["random", "none"]]
    continue_previous: Literal["new", "hold", "evolve"]

class MusicDirective(BaseModel):
    caption: str
    ambience_cue: str
    duck_under_voice: bool
    segment_id: str

class Beat(BaseModel):
    id: str
    type: Literal["narration", "silence", "beat_only", "chapter_break"]
    chapter_id: str
    title: str # "none" if no title
    note: str
    duration: Union[float, Literal["pending", "none"]] # "pending" for narration, float (seconds) for others
    
    dialogue: Union[str, Literal["none"]]
    voice: Union[VoiceDirective, Literal["none"]]
    image: Union[ImageDirective, Literal["none"]]
    music: Union[MusicDirective, Literal["none"]]

class BeatsManifest(BaseModel):
    beats: List[Beat]
```

CRITICAL COMPILATION RULES:
1. Every beat MUST have ALL fields (dialogue, voice, image, music). If a field doesn't apply to the beat type, use "none".
2. For "narration" beats, duration MUST be "pending".
3. For non-narration beats (silence, beat_only, chapter_break), duration MUST be a float (seconds).
4. Parse the values from the Markdown file exactly as specified. Do not summarize or combine beats.
5. Return ONLY a valid JSON object with the top-level key "beats". Do not include markdown formatting or extra text outside the JSON.
"""

def compile_plan_to_manifest(plan_path: str, output_name: str = "manifest.json", local: bool = False) -> str:
    with open(plan_path, "r") as f:
        plan_text = f.read()

    print("Sending structured plan to Director Stage 0B (Formatter)...")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_FORMATTER},
        {"role": "user", "content": f"Here is the structured markdown plan to compile into JSON:\n\n{plan_text}"}
    ]
    
    # We use Qwen3-32B FP8 for JSON formatting
    model_name = "repos/Qwen3-32B-FP8" if local else "gpt-4o"
    
    # Call the model via our lifecycle client
    raw_json = run_completion_with_lifecycle(
        model_name=model_name,
        messages=messages,
        temperature=0.1,  # Low temperature for precise transcription
        local=local,
        response_format={ "type": "json_object" }
    )
    
    os.makedirs(PATHS["manifests_dir"], exist_ok=True)
    out_path = os.path.join(PATHS["manifests_dir"], output_name)
    
    with open(out_path, "w") as f:
        f.write(raw_json)
        
    print(f"Manifest JSON saved to {out_path}")
    
    # Validate against our Pydantic model
    try:
        manifest = BeatsManifest.model_validate_json(raw_json)
        print(f"Success! Validated {len(manifest.beats)} beats in the final manifest.")
        return out_path
    except Exception as e:
        print("Warning: The generated JSON failed Pydantic validation:")
        print(e)
        return None

if __name__ == "__main__":
    plan_p = os.path.join(PATHS["manifests_dir"], "director_plan.md")
    use_local = "--local" in sys.argv
    compile_plan_to_manifest(plan_p, local=use_local)
