#!/bin/bash

# Ensure the script exits if any command fails
set -e

# Define the name of the executable and the main Python script
EXECUTABLE_NAME="FreeScribe"
MAIN_SCRIPT="src/FreeScribe.client/client.py"
ICON_PATH="src/FreeScribe.client/assets/logo.ico"
MODEL_URL="https://huggingface.co/lmstudio-community/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q8_0.gguf?download=true"

# Run PyInstaller to create the standalone executable
pyinstaller --additional-hooks-dir=./scripts/hooks \
  --add-data "./scripts/NVIDIA_INSTALL.txt:install_state" \
  --add-data "./src/FreeScribe.client/whisper-assets:faster_whisper/assets" \
  --add-data "./src/FreeScribe.client/markdown:markdown" \
  --add-data "./src/FreeScribe.client/assets:assets" \
  --add-data "/home/invain/.virtualenvs/freescribe/lib/python3.10/site-packages/nvidia:nvidia-drivers" \
  --hidden-import PIL._tkinter_finder \
  --hidden-import PIL.ImageTk \
  --name "$EXECUTABLE_NAME" \
  --icon="$ICON_PATH" \
  --noconsole \
  --noconfirm \
  "$MAIN_SCRIPT"


# Print a message indicating that the build is complete
echo "Build complete. Executable created: dist/FreeScribe/$EXECUTABLE_NAME"
