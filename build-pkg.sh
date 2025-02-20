#!/bin/bash

# Ensure the script exits if any command fails
set -e

usage() {
    echo "Usage: $0 --arch <arm64|x86_64>"
    exit 1
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift
            ;;
        *)
            usage
            ;;
    esac
    shift
done

# Check if arch argument is provided
if [[ -z "$ARCH" ]]; then
    usage
fi

case $ARCH in
    arm64)
        echo "Building for Apple Silicon-based Macs"
        ;;
    x86_64)
        echo "Building for Intel-based Macs"
        ;;
    *)
        usage
        ;;
esac

DIR_NAME="dist/client"
IDENTIFIER="com.clinicianfocus.freescribe"

# Create a directory to store the built application and move the app into it
echo "Creating directory $DIR_NAME"
mkdir -p $DIR_NAME

echo "Creating directory dist/installer"
mkdir -p dist/installer

echo "Moving app to $DIR_NAME"
mv dist/freescribe-client.app $DIR_NAME

# Build pkg installer for macOS using the pkgbuild command
pkgbuild --root $DIR_NAME \
    --identifier $IDENTIFIER \
    --scripts ./mac/scripts/ \
    --version 1.0 \
    --install-location /Applications \
    ./dist/installer/installer.pkg

echo "Build complete. Installer created: dist/installer.pkg"

# Build the final installer package using the productbuild command
case $ARCH in
    arm64)
        productbuild --distribution ./mac/distribution-arm64.xml \
            --package-path ./dist/installer/ \
            --resources ./mac/resources/ \
            ./dist/FreeScribeInstaller.pkg
        ;;
    x86_64)
        productbuild --distribution ./mac/distribution-x86_64.xml \
            --package-path ./dist/installer/ \
            --resources ./mac/resources/ \
            ./dist/FreeScribeInstaller.pkg
        ;;
    *)
        usage
        ;;
esac

echo "Build complete. Final installer package created: dist/FreeScribeInstaller.pkg"