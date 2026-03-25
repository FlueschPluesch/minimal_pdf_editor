#!/usr/bin/env bash

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
python3 -m pip install PyQt6 PyMuPDF pyinstaller --quiet

echo "Building PDF Editor executable..."
pyinstaller --noconfirm --onefile --windowed --name "PDF Editor" main.py

echo "Build complete! You can find the executable in the 'dist' folder."
