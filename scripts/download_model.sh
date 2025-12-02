#!/bin/bash
#
# Download a tiny LLM model for local inference
# 
# Usage:
#   ./scripts/download_model.sh                    # Download default TinyLlama model
#   MODEL_URL=https://... ./scripts/download_model.sh  # Download custom model
#
# Offline Usage:
#   Place your GGUF model file directly into ./models/local-llm/model.gguf
#
# Model Options (smallest to largest):
#   - TinyLlama 1.1B Q4_K_M (~600MB) - DEFAULT, best for laptops
#   - Phi-2 Q4_K_M (~1.5GB) - Better quality, needs more RAM
#   - Mistral 7B Q4_K_M (~4GB) - Much better quality, needs 8GB+ RAM
#

set -e

MODEL_DIR="./models/local-llm"
MODEL_FILE="$MODEL_DIR/model.gguf"

# Default: Qwen1.5-1.8B-Chat - Better quality, still small (~1.2GB)
DEFAULT_MODEL_URL="https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat-q4_k_m.gguf"
# Checksum verification disabled for new model
DEFAULT_CHECKSUM=""

# Allow override via environment variable
MODEL_URL="${MODEL_URL:-$DEFAULT_MODEL_URL}"
EXPECTED_CHECKSUM="${MODEL_CHECKSUM:-$DEFAULT_CHECKSUM}"

echo "=============================================="
echo "Local LLM Model Downloader"
echo "=============================================="
echo ""

# Create model directory
mkdir -p "$MODEL_DIR"

# Check if model already exists
if [ -f "$MODEL_FILE" ]; then
    echo "✓ Model already exists at $MODEL_FILE"
    echo "  Size: $(du -h "$MODEL_FILE" | cut -f1)"
    echo ""
    echo "To re-download, remove the file first:"
    echo "  rm $MODEL_FILE"
    exit 0
fi

echo "Downloading model..."
echo "  URL: $MODEL_URL"
echo "  Target: $MODEL_FILE"
echo ""

# Check if curl or wget is available
if command -v curl &> /dev/null; then
    curl -L -# -o "$MODEL_FILE" "$MODEL_URL"
elif command -v wget &> /dev/null; then
    wget -q --show-progress -O "$MODEL_FILE" "$MODEL_URL"
else
    echo "ERROR: Neither curl nor wget is available"
    echo ""
    echo "Manual download instructions:"
    echo "  1. Download from: $MODEL_URL"
    echo "  2. Save to: $MODEL_FILE"
    exit 1
fi

# Verify download
if [ ! -f "$MODEL_FILE" ]; then
    echo "ERROR: Download failed - file not found"
    exit 1
fi

FILE_SIZE=$(du -h "$MODEL_FILE" | cut -f1)
echo ""
echo "✓ Download complete!"
echo "  File: $MODEL_FILE"
echo "  Size: $FILE_SIZE"

# Optional checksum verification (skip if checksum not provided or different model)
if [ "$MODEL_URL" = "$DEFAULT_MODEL_URL" ] && command -v sha256sum &> /dev/null; then
    echo ""
    echo "Verifying checksum..."
    ACTUAL_CHECKSUM="sha256:$(sha256sum "$MODEL_FILE" | cut -d' ' -f1)"
    if [ "$ACTUAL_CHECKSUM" = "$EXPECTED_CHECKSUM" ]; then
        echo "✓ Checksum verified"
    else
        echo "⚠ Checksum mismatch (this may be OK if the model was updated)"
        echo "  Expected: $EXPECTED_CHECKSUM"
        echo "  Got:      $ACTUAL_CHECKSUM"
    fi
fi

echo ""
echo "=============================================="
echo "Model ready! You can now start the local LLM:"
echo "  docker compose up local-llm"
echo "=============================================="
