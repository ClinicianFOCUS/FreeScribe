#!/bin/bash

# Ensure the script exits if any command fails
set -e

# Define the name of the executable and the main Python script
EXECUTABLE_NAME="FreeScribe"
MAIN_SCRIPT="src/FreeScribe.client/client.py"
ICON_PATH="src/FreeScribe.client/assets/logo.ico"

# Run PyInstaller to create the standalone executable
pyinstaller client-mac.spec --noconfirm

# Print a message indicating that the build is complete
echo "Build complete. Executable created: $DIST_PATH/$EXECUTABLE_NAME.app"