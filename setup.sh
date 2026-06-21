#!/bin/bash
set -e

echo "================================================================"
echo "          Ellora System - Zero-Touch Setup Script"
echo "================================================================"

# 1. Ensure 'uv' is installed
if ! command -v uv &> /dev/null; then
    echo "[1/5] Installing 'uv' package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
else
    echo "[1/5] 'uv' package manager is already installed."
fi

# 2. Setup repos directory
echo "[2/5] Setting up third-party repositories..."
mkdir -p repos
cd repos

# Clone index-tts if not present
if [ ! -d "index-tts" ]; then
    echo "      Cloning index-tts..."
    git clone https://github.com/index-tts/index-tts.git
else
    echo "      index-tts already cloned."
fi
cd ..

# 3. Patch index-tts
echo "[3/5] Patching index-tts for transformers v4.49+ compatibility..."
if [ -f "scripts/patch_indextts.py" ]; then
    python scripts/patch_indextts.py
else
    echo "      Warning: scripts/patch_indextts.py not found. Make sure you are in the elloraa root directory."
fi

# 4. Sync Python Environment
echo "[4/5] Syncing Python dependencies using uv..."
uv sync

# 5. Model Downloads
echo "[5/5] Checking for required LLM models..."
if [ ! -d "repos/DeepSeek-R1-Distill-Qwen-32B-FP8" ]; then
    echo "      Warning: DeepSeek-R1-Distill-Qwen-32B-FP8 not found in repos/."
    echo "      Please download it via huggingface-cli:"
    echo "      uv run huggingface-cli download neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8 --local-dir repos/DeepSeek-R1-Distill-Qwen-32B-FP8"
fi

if [ ! -d "repos/Qwen3-32B-FP8" ]; then
    echo "      Warning: Qwen3-32B-FP8 not found in repos/."
    echo "      Please download it via huggingface-cli:"
    echo "      uv run huggingface-cli download neuralmagic/Qwen2.5-32B-Instruct-FP8 --local-dir repos/Qwen3-32B-FP8"
fi

echo "================================================================"
echo "Setup Complete! You can now run the Ellora pipeline."
echo "================================================================"
