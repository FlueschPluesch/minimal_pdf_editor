#!/usr/bin/env bash

# Run this script to generate a single executable file for the PDF Editor App
echo "Updating build version..."
if [ -f "version.json" ]; then
    # Use python to safely increment build number in JSON
    python3 -c "import json; f=open('version.json','r+'); v=json.load(f); v['build_number']+=1; f.seek(0); json.dump(v,f); f.truncate(); print(f'New Build Number: {v[\"build_number\"]}')"
else
    echo '{"build_number": 1, "year": 2026}' > version.json
    echo "Initialized version.json with Build Number 1"
fi

echo "Setting up environment for PDF Editor..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in your PATH. Please install Python 3.10+ and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or upgrade dependencies
echo "Installing/Upgrading dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install PyQt6 PyMuPDF pyinstaller Pillow --quiet

# Convert icon.png to icon.ico if it exists (high-quality multi-resolution)
if [ -f "icon.png" ]; then
    echo "Converting icon.png to icon.ico (high-quality)..."
    python3 -c "from PIL import Image; img = Image.open('icon.png').convert('RGBA'); side = max(img.size); square = Image.new('RGBA', (side, side), (0,0,0,0)); square.paste(img, ((side - img.width)//2, (side - img.height)//2)); square.save('icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"
fi

# Clean up old spec files
rm -f *.spec

echo "Building Minimal PDF Editor executable..."
PYINSTALLER_ARGS=("--noconfirm" "--onefile" "--windowed")

if [ -f "icon.ico" ]; then
    PYINSTALLER_ARGS+=("--icon" "icon.ico")
fi

PYINSTALLER_ARGS+=("--name" "Minimal PDF Editor")
# Note: Path separator for --add-data is ':' on Linux/Mac
PYINSTALLER_ARGS+=("--add-data" "version.json:.")
PYINSTALLER_ARGS+=("--add-data" "icon.png:.")
PYINSTALLER_ARGS+=("main.py")

pyinstaller "${PYINSTALLER_ARGS[@]}"

echo "Build complete! You can find the executable in the 'dist' folder."
