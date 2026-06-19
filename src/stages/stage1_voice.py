import os
import sys

# Assume the user cloned 'index-tts' in the root alongside 'src'
sys.path.append(os.path.abspath("index-tts"))

try:
    from indextts.infer_v2 import IndexTTS2
except ImportError:
    print("Warning: index-tts not found. Ensure it is cloned and dependencies are installed.")
    IndexTTS2 = None

from src.config import PATHS

class VoiceEngine:
    def __init__(self):
        # Fallback handling in case the user hasn't downloaded the models yet
        cfg_path = "index-tts/checkpoints/config.yaml"
        model_dir = "index-tts/checkpoints"
        
        if not os.path.exists(cfg_path) or not IndexTTS2:
            self.tts = None
            print(f"Warning: TTS Model not loaded. Could not find config at {cfg_path}")
            return
            
        print("Initializing IndexTTS2...")
        self.tts = IndexTTS2(
            cfg_path=cfg_path,
            model_dir=model_dir,
            use_fp16=True, # Recommended by docs for speed/vram
            use_cuda_kernel=False,
            use_deepspeed=False,
        )
        print("IndexTTS2 initialized successfully.")

    def generate_narration(self, text: str, tone: str, intensity: float, output_filename: str):
        if not self.tts:
            print("Mock Voice Engine: Would have generated audio for:", text)
            return True
            
        output_path = os.path.join(PATHS["audio_dir"], output_filename)
        os.makedirs(PATHS["audio_dir"], exist_ok=True)
        
        # We only have 'serious_tone.wav' right now. 
        # In the future, we would map `tone` to the correct file.
        reference_audio = os.path.join(PATHS["voices_dir"], "serious_tone.wav")
        
        if not os.path.exists(reference_audio):
            print(f"Error: Reference audio not found at {reference_audio}")
            return False

        # Map tone to emotion vector based on the docs: 
        # [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
        emo_vector = [0, 0, 0, 0, 0, 0, 0, 0]
        
        # We'll use intensity to drive the vector strength
        if tone == "serious":
            # Serious is a mix of calm and maybe slightly melancholic depending on the script
            emo_vector = [0, 0, 0, 0, 0, intensity * 0.3, 0, intensity * 0.8]
        elif tone == "calm":
            emo_vector = [0, 0, 0, 0, 0, 0, 0, intensity]
        elif tone == "soft_laugh":
            emo_vector = [intensity * 0.4, 0, 0, 0, 0, 0, 0, intensity * 0.5]
            
        try:
            print(f"Generating TTS for: '{text[:30]}...' -> {output_filename}")
            self.tts.infer(
                spk_audio_prompt=reference_audio,
                text=text,
                output_path=output_path,
                emo_vector=emo_vector,
                use_random=False, # Per docs, disables stochasticity to maintain fidelity
                verbose=False
            )
            return True
        except Exception as e:
            print(f"TTS Generation failed: {e}")
            return False

def test_voice_stage():
    print("--- Starting Voice Stage Test ---")
    engine = VoiceEngine()
    
    test_text = "The tropical rain fell in drenching sheets, hammering the corrugated roof of the clinic building."
    print("\nTest Text:", test_text)
    print("Tone: serious (intensity: 0.8)")
    
    success = engine.generate_narration(
        text=test_text,
        tone="serious",
        intensity=0.8,
        output_filename="test_output.wav"
    )
    
    if success:
        print(f"\nSuccess! Check {PATHS['audio_dir']}/test_output.wav")
    else:
        print("\nFailed to generate audio.")

if __name__ == "__main__":
    test_voice_stage()
