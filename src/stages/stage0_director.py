import json
import os
from src.config import client, PATHS
from src.manifest import BeatsManifest

SYSTEM_PROMPT = """You are the Director for an autonomous AI documentary production pipeline.
You must read the provided script and output a fully populated Beats Manifest in JSON format.

The manifest must be a single JSON object with a key "beats" containing a list of beat objects.
The output will be parsed into this Pydantic schema:

```python
class VoiceDirective(BaseModel):
    tone: Literal["serious", "curious", "normal", "calm", "soft_laugh"]
    intensity: float # 0.0 to 1.0
    tone_module_ref: str
    emphasis_words: List[str]
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
    duration: Union[float, Literal["pending", "none"]] # "pending" for narration
    
    dialogue: Union[str, Literal["none"]]
    voice: Union[VoiceDirective, Literal["none"]]
    image: Union[ImageDirective, Literal["none"]]
    music: Union[MusicDirective, Literal["none"]]
```

CRITICAL RULES:
1. Every beat MUST have ALL fields (dialogue, voice, image, music). If a field doesn't apply to the beat type, use "none". 
2. For "narration" beats, duration MUST be "pending".
3. For non-narration beats, duration MUST be a float (seconds).
4. Break the script down sentence by sentence or phrase by phrase.
5. Create a tense, atmospheric visual style in prompt_description (eerie, cinematic, painterly).
6. Set segment_ids for music to group beats into contiguous musical sections.
7. Return ONLY valid JSON with the top-level key "beats". Do not include markdown formatting or extra text outside the JSON.
"""

def generate_manifest(script_path: str, output_name: str = "manifest.json"):
    with open(script_path, "r") as f:
        script_text = f.read()

    print("Sending script to Director Pass (OpenAI)...")
    
    response = client.chat.completions.create(
        model="gpt-4o", # Using 4o for large context window and strong JSON adherence
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the script to process:\n\n{script_text}"}
        ],
        response_format={ "type": "json_object" },
        temperature=0.7
    )
    
    raw_json = response.choices[0].message.content
    
    # Save the raw output
    os.makedirs(PATHS["manifests_dir"], exist_ok=True)
    out_path = os.path.join(PATHS["manifests_dir"], output_name)
    
    with open(out_path, "w") as f:
        f.write(raw_json)
        
    print(f"Manifest saved to {out_path}")
    
    # Validate against our Pydantic model
    try:
        manifest = BeatsManifest.model_validate_json(raw_json)
        print(f"Success! Validated {len(manifest.beats)} beats in the manifest.")
        return manifest
    except Exception as e:
        print("Warning: The generated JSON failed Pydantic validation:")
        print(e)
        return None

if __name__ == "__main__":
    generate_manifest(os.path.join(PATHS["scripts_dir"], "script.md"))
