import os
import sys
import time
import shutil
import wave

# Assume the user cloned 'index-tts' inside the repos/ 
try:
    from indextts.infer_v2 import IndexTTS2
except ImportError:
    print("Warning: index-tts not found. Ensure it is cloned and dependencies are installed.")
    IndexTTS2 = None

from src.config import PATHS
from src.manifest import BeatsManifest

class VoiceEngine:
    def __init__(self):
        cfg_path = "repos/index-tts/checkpoints/config.yaml"
        model_dir = "repos/index-tts/checkpoints"
        
        if not os.path.exists(cfg_path) or not IndexTTS2:
            self.tts = None
            print(f"Warning: TTS Model not loaded. Could not find config at {cfg_path}")
            return
            
        print("Initializing IndexTTS2...")
        self.tts = IndexTTS2(
            cfg_path=cfg_path,
            model_dir=model_dir,
            use_fp16=False, # Recommended by docs for speed/vram
            use_cuda_kernel=True,
            use_deepspeed=False,
        )
        print("IndexTTS2 initialized successfully.")

    def generate_narration(self, text: str, tone: str, intensity: float, output_filename: str, emo_alpha: float = 0.75):
        if not self.tts:
            raise RuntimeError("IndexTTS2 model is not loaded. Cannot generate audio.")
            
        output_path = os.path.join(PATHS["audio_dir"], output_filename)
        os.makedirs(PATHS["audio_dir"], exist_ok=True)
        
        # Reference voice is resolved dynamically based on the tone: assets/voices/{tone}_tone.wav
        reference_filename = f"{tone}_tone.wav"
        reference_audio = os.path.join(PATHS["voices_dir"], reference_filename)
        if not os.path.exists(reference_audio):
            print(f"Error: Reference audio not found at {reference_audio}")
            return False

        # Map tone to its custom tweaked emotion vector:
        # [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
        if tone == "calm":
            emo_vector = [0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0, intensity * 0.8]
        elif tone == "curious":
            emo_vector = [0.0, 0.0, 0.1, 0.15, 0.0, intensity * 0.45, 0.0, intensity * 0.3]
        elif tone == "soft_laugh":
            emo_vector = [intensity * 0.6, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, intensity * 0.2]
        else:
            emo_vector = [0.0, 0.0, 0.1, 0.15, 0.0, intensity * 0.45, 0.0, intensity * 0.3]
            
        try:
            print(f"Generating TTS for: '{text[:30]}...' -> {output_filename}")
            self.tts.infer(
                spk_audio_prompt=reference_audio,
                text=text,
                output_path=output_path,
                emo_vector=emo_vector,
                emo_alpha=emo_alpha,
                use_random=False, # Per docs, disables stochasticity to maintain fidelity
                verbose=False
            )
            return True
        except Exception as e:
            print(f"TTS Generation failed: {e}")
            return False

def get_wav_duration(filepath: str) -> float:
    try:
        with wave.open(filepath, 'r') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return round(duration, 3)
    except Exception as e:
        print(f"Error reading duration for {filepath}: {e}")
        return 0.0

def run_voice_stage():
    manifest_path = os.path.join(PATHS["manifests_dir"], "manifest.json")
    
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found at {manifest_path}")
        return

    # 1. Backup the manifest
    timestamp = int(time.time())
    backup_path = os.path.join(PATHS["manifests_dir"], f"manifest_backup_{timestamp}.json")
    shutil.copy2(manifest_path, backup_path)
    print(f"Created manifest backup at: {backup_path}")

    # 2. Load the manifest
    print("Loading manifest...")
    manifest = BeatsManifest.load_from_file(manifest_path)
    
    # 3. Initialize Voice Engine
    engine = VoiceEngine()
    if not engine.tts:
        raise RuntimeError("Failed to load IndexTTS2 model. Cannot process voice stage.")
    
    os.makedirs(PATHS["audio_dir"], exist_ok=True)

    # 4. Process beats
    for beat in manifest.beats:
        if beat.type == "narration" and beat.voice != "none":
            output_filename = f"{beat.id}.wav"
            output_path = os.path.join(PATHS["audio_dir"], output_filename)
            
            print(f"Processing beat {beat.id} (tone: {beat.voice.tone}, intensity: {beat.voice.intensity})...")
            
            success = engine.generate_narration(
                text=beat.dialogue,
                tone=beat.voice.tone,
                intensity=beat.voice.intensity,
                output_filename=output_filename
            )
            
            if success:
                # Measure the actual duration
                if os.path.exists(output_path):
                    duration = get_wav_duration(output_path)
                    beat.duration = duration
                    print(f"  -> Measured duration: {duration}s")
                else:
                    raise FileNotFoundError(f"Expected generated audio file at {output_path} but it was not found.")
            else:
                raise RuntimeError(f"Failed to generate audio for {beat.id}")

    # 5. Save mutated manifest back to the same path
    print("Saving updated manifest...")
    manifest.save_to_file(manifest_path)
    print("Voice stage completed successfully.")

if __name__ == "__main__":
    run_voice_stage()
