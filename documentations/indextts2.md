# IndexTTS2 Essentials

## Official source
 Use the official repository as the main source of documentation: `https://github.com/index-tts/index-tts`.[cite:1]

## Install

The documented setup requires `git`, `git-lfs`, and `uv`.[cite:1]

```bash
git lfs install
git clone https://github.com/index-tts/index-tts.git && cd index-tts
git lfs pull
pip install -U uv
uv sync --all-extras
```

The README says the `uv` path is the officially supported installation method.[cite:1]

## Download model

### Hugging Face

```bash
uv tool install "huggingface-hub[cli,hf_xet]"
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

### ModelScope

```bash
uv tool install "modelscope"
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

The examples use `checkpoints/config.yaml` and `checkpoints/` as the config path and model directory.[cite:1]

## WebUI

```bash
uv run webui.py
```

The documented default address is `http://127.0.0.1:7860`.[cite:1]

## Python entry point

```python
from indextts.infer_v2 import IndexTTS2
```

```python
tts = IndexTTS2(
    cfg_path="checkpoints/config.yaml",
    model_dir="checkpoints",
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
)
```

## Basic inference

```python
text = "Translate for me, what is a surprise!"

tts.infer(
    spk_audio_prompt="examples/voice_01.wav",
    text=text,
    output_path="gen.wav",
    verbose=True,
)
```

## Main inference arguments

| Argument | Meaning |
|---|---|
| `spk_audio_prompt` | Speaker reference audio.[cite:1] |
| `text` | Text to synthesize.[cite:1] |
| `output_path` | Output WAV path.[cite:1] |
| `emo_audio_prompt` | Emotion reference audio.[cite:1] |
| `emo_alpha` | Emotion strength, documented range `0.0 - 1.0`, default `1.0`.[cite:1] |
| `emo_vector` | Eight-value emotion vector.[cite:1] |
| `use_random` | Enables stochasticity; the README warns it reduces voice-cloning fidelity.[cite:1] |
| `use_emo_text` | Uses text-based emotion guidance.[cite:1] |
| `emo_text` | Separate text description for emotion control.[cite:1] |
| `verbose` | Verbose logging.[cite:1] |

## Emotion modes

### Emotion reference audio

```python
tts.infer(
    spk_audio_prompt="examples/voice_07.wav",
    text=text,
    output_path="gen.wav",
    emo_audio_prompt="examples/emo_sad.wav",
    verbose=True,
)
```

### Emotion reference audio with strength

```python
tts.infer(
    spk_audio_prompt="examples/voice_07.wav",
    text=text,
    output_path="gen.wav",
    emo_audio_prompt="examples/emo_sad.wav",
    emo_alpha=0.9,
    verbose=True,
)
```

### Emotion vector

The documented vector order is `[happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]`.[cite:1]

```python
tts.infer(
    spk_audio_prompt="examples/voice_10.wav",
    text=text,
    output_path="gen.wav",
    emo_vector=[0, 0, 0, 0, 0, 0, 0.45, 0],
    use_random=False,
    verbose=True,
)
```

### Emotion from text

```python
tts.infer(
    spk_audio_prompt="examples/voice_12.wav",
    text=text,
    output_path="gen.wav",
    emo_alpha=0.6,
    use_emo_text=True,
    use_random=False,
    verbose=True,
)
```

### Separate emotion description text

```python
emo_text = "你吓死我了！你是鬼吗？"

tts.infer(
    spk_audio_prompt="examples/voice_12.wav",
    text=text,
    output_path="gen.wav",
    emo_alpha=0.6,
    use_emo_text=True,
    emo_text=emo_text,
    use_random=False,
    verbose=True,
)
```

The README recommends `emo_alpha` around `0.6` or lower for more natural speech in text-based emotion modes.[cite:1]

## Notes

- `use_fp16` is recommended in the README because it usually reduces VRAM usage and speeds up inference with only a small quality tradeoff.[cite:1]
- `use_deepspeed` is optional and may help or hurt performance depending on hardware and drivers.[cite:1]
- Mixed Chinese character and Pinyin input is supported, and valid Pinyin combinations are listed in `checkpoints/pinyin.vocab`.[cite:1]
