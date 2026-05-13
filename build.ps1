# Run this script to generate a single executable file for the PDF Editor App
Write-Host "Updating build version..."
$versionFile = ".\version.json"
if (Test-Path $versionFile) {
    $version = Get-Content $versionFile | ConvertFrom-Json
    $version.build_number = [int]$version.build_number + 1
    $version.year = (Get-Date).Year
    $version | ConvertTo-Json | Set-Content $versionFile
    Write-Host "New Build Number: $($version.build_number)"
} else {
    $version = @{ build_number = 1; year = (Get-Date).Year }
    $version | ConvertTo-Json | Set-Content $versionFile
    Write-Host "Initialized version.json with Build Number 1"
}

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
.\venv\Scripts\python.exe -m pip install PyQt6 PyMuPDF pyinstaller Pillow --quiet

# Convert icon.png to icon.ico if it exists (high-quality multi-resolution)
if (Test-Path ".\icon.png") {
    Write-Host "Converting icon.png to icon.ico (high-quality)..."
    .\venv\Scripts\python.exe -c "from PIL import Image; img = Image.open('icon.png').convert('RGBA'); side = max(img.size); square = Image.new('RGBA', (side, side), (0,0,0,0)); square.paste(img, ((side - img.width)//2, (side - img.height)//2)); square.save('icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"
}

# Clean up old spec files to ensure a fresh build with the new icon settings
Remove-Item -Path "*.spec" -ErrorAction SilentlyContinue

Write-Host "Building Minimal PDF Editor executable..."
$pyinstaller = ".\venv\Scripts\pyinstaller.exe"
$args = @("--noconfirm", "--onefile", "--windowed")

if (Test-Path ".\icon.ico") {
    $args += "--icon", "icon.ico"
}

$args += "--name", "Minimal PDF Editor"
$args += "--add-data", "version.json;."
$args += "--add-data", "icon.png;."
$args += ".\main.py"

& $pyinstaller $args

# Update github_export folder with latest source and project files
Write-Host "Updating github_export folder..."
$exportDir = ".\github_export"
if (!(Test-Path -Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir | Out-Null
}

$filesToCopy = @("main.py", "build.ps1", "build.sh", "version.json", "icon.png", "LICENSE", "README.md", ".gitignore")

foreach ($file in $filesToCopy) {
    if (Test-Path ".\$file") {
        Copy-Item -Path ".\$file" -Destination "$exportDir\$file" -Force
    }
}
Write-Host "github_export folder updated."

Write-Host "Build complete! You can find the executable in the 'dist' folder."