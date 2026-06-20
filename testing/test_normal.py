import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from indextts.infer_v2 import IndexTTS2
except ImportError:
    print("Error: indextts package not found. Make sure you are running via 'uv run' or in a synchronized virtual environment.")
    sys.exit(1)

# Configurable Test Parameters
TEXT = "The expedition team set up their camp at the base of the mountain at sunset."
INTENSITY = 0.5  # Lower default intensity for normal/neutral speech
EMO_ALPHA = 0.75  # Emotion mixing parameter (0.0 to 1.0)
OUTPUT_FILENAME = "test_normal.wav"

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    cfg_path = os.path.join(project_root, "repos/index-tts/checkpoints/config.yaml")
    model_dir = os.path.join(project_root, "repos/index-tts/checkpoints")
    voice_ref = os.path.join(project_root, "assets/voices/normal_tone.wav")
    output_dir = os.path.join(project_root, "testing/outputs")
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)

    print("--- IndexTTS2 Normal Tone Test ---")
    print(f"Text: '{TEXT}'")
    print(f"Intensity: {INTENSITY} | Emo Alpha: {EMO_ALPHA}")

    # Validate paths
    if not os.path.exists(cfg_path):
        print(f"Error: Model checkpoints not found at '{cfg_path}'. Please ensure index-tts model checkpoints are downloaded.")
        sys.exit(1)
    if not os.path.exists(voice_ref):
        print(f"Error: Normal reference voice not found at '{voice_ref}'.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print("Initializing IndexTTS2...")
    tts = IndexTTS2(
        cfg_path=cfg_path,
        model_dir=model_dir,
        use_fp16=True,
        use_cuda_kernel=False,
        use_deepspeed=False,
    )

    # Map normal tone to emotion vector:
    # [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
    # Keep it neutral with just a very small amount of calm
    emo_vector = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, INTENSITY * 0.2]
    print(f"Emotion vector: {emo_vector}")

    try:
        print("Generating audio...")
        tts.infer(
            spk_audio_prompt=voice_ref,
            text=TEXT,
            output_path=output_path,
            emo_vector=emo_vector,
            emo_alpha=EMO_ALPHA,
            use_random=False,
            verbose=True
        )
        print(f"Success! Output saved to: {output_path}")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    main()
