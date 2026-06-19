#!/bin/bash

echo "=== Ellora Pipeline: Cloud PC Setup Script ==="

# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y git git-lfs ffmpeg

# 2. Install UV (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 3. Set up the Ellora project
uv sync
uv add pydantic openai

# 4. Clone and setup IndexTTS2
git lfs install
git clone https://github.com/index-tts/index-tts.git
cd index-tts
git lfs pull
uv pip install -e . # Install indextts as an editable package so our src/ code can import it
cd ..

# 5. Download the Model Checkpoints
uv tool install "huggingface-hub[cli,hf_xet]"
hf download IndexTeam/IndexTTS-2 --local-dir=index-tts/checkpoints

echo ""
echo "=== Setup Complete! ==="
echo "To test the voice stage, run:"
echo "uv run python src/stages/stage1_voice.py"
