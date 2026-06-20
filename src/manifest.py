from typing import Literal, Optional, List, Union
from pydantic import BaseModel, Field

BeatType = Literal["narration", "silence", "beat_only", "chapter_break"]

class VoiceDirective(BaseModel):
    tone: Literal["curious", "calm", "soft_laugh"]
    intensity: float = Field(ge=0.0, le=1.0)
    pause_after: float

class ImageDirective(BaseModel):
    prompt_keywords: str
    prompt_description: str
    negative_prompt: str
    lora: str
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
    type: BeatType
    chapter_id: str
    title: str
    note: str
    duration: Union[float, Literal["pending", "none"]]
    
    dialogue: Union[str, Literal["none"]]
    voice: Union[VoiceDirective, Literal["none"]]
    image: Union[ImageDirective, Literal["none"]]
    music: Union[MusicDirective, Literal["none"]]

class BeatsManifest(BaseModel):
    beats: List[Beat]

    def save_to_file(self, filepath: str):
        with open(filepath, "w") as f:
            f.write(self.model_dump_json(indent=2))
            
    @classmethod
    def load_from_file(cls, filepath: str) -> "BeatsManifest":
        with open(filepath, "r") as f:
            return cls.model_validate_json(f.read())
