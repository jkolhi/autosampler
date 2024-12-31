#!/bin/bash

# Exit on error
set -e

echo "Starting build process..."

# Clean previous builds
rm -rf build dist

# Ensure PortAudio is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if ! brew list portaudio &> /dev/null; then
    echo "Installing PortAudio..."
    brew install portaudio
fi

# Get PortAudio library path
PORTAUDIO_PATH=$(brew --prefix portaudio)
echo "PortAudio installed at: $PORTAUDIO_PATH"

# Update spec file with correct paths
sed -i '' "s|/usr/local/lib/libportaudio|$PORTAUDIO_PATH/lib/libportaudio|g" autosampler.spec

# Create Mac app bundle
echo "Building application..."
pyinstaller autosampler.spec

# Verify app exists before signing
if [ -d "dist/AudioAutoSampler.app" ]; then
    echo "Signing application..."
    codesign --force --deep --sign - "dist/AudioAutoSampler.app"
    echo "Build complete! App is in dist/AudioAutoSampler.app"
else
    echo "Error: Application bundle not created"
    exit 1
fi