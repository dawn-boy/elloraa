import os
import time
import shutil
import wave
from src.config import PATHS
from src.manifest import BeatsManifest
from src.stages.stage1_voice import VoiceEngine

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
    
    os.makedirs(PATHS["audio_dir"], exist_ok=True)

    # 4. Process beats
    for beat in manifest.beats:
        if beat.type == "narration" and beat.voice != "none":
            # The user requested to focus on the serious tone for now
            if beat.voice.tone == "serious":
                output_filename = f"{beat.id}.wav"
                output_path = os.path.join(PATHS["audio_dir"], output_filename)
                
                print(f"Processing beat {beat.id} (tone: {beat.voice.tone})...")
                
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
            else:
                print(f"Skipping beat {beat.id} - tone is '{beat.voice.tone}', only processing 'serious' currently.")

    # 5. Save mutated manifest back to the same path
    print("Saving updated manifest...")
    manifest.save_to_file(manifest_path)
    print("Voice stage completed successfully.")

if __name__ == "__main__":
    run_voice_stage()
