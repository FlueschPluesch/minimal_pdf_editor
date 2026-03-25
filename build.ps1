# Run this script to generate a single executable file for the PDF Editor App
Write-Host "Setting up environment for PDF Editor..."

# Ensure Python is available
if (!(Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in your PATH. Please install Python 3.10+ and try again."
    exit 1
}

# Create virtual environment if it doesn't exist
if (!(Test-Path -Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Install or upgrade dependencies
Write-Host "Installing/Upgrading dependencies..."
.\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.\venv\Scripts\python.exe -m pip install PyQt6 PyMuPDF pyinstaller --quiet

Write-Host "Building PDF Editor executable..."
.\venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name "PDF Editor" .\main.py

Write-Host "Build complete! You can find the executable in the 'dist' folder."