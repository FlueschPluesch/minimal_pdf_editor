# PDF Editor

A fully standalone, cross-platform PDF Editor application written in Python and PyQt6. This powerful tool allows you to deeply modify existing PDF documents, freely draw and add graphics, and manage pages directly on your device.

## Features

- **Edit existing content:** Select, modify, move, scale, and rotate existing text, images, and vector graphics extracted straight from the source PDF.
- **Draw primitives:** Add and configure straight lines, rectangles, circles, and triangles with customized border widths (Line Width) and background colors (Fill: ON/OFF).
- **Freehand brush tool:** Paint directly onto your documents using a completely customizable vector brush that supports later scaling, coloring, and rotating.
- **Add custom text and checkmarks:** Insert multiline text, scalable "check" (✅) or "cross" (❌) markings.
- **Media and Signatures:** Import local images (`.png`, `.jpg`, etc.) or define a persistent personal signature image to quickly sign multiple documents.
- **Page Management:** Insert a blank page, delete an unwanted page, or import an entire secondary PDF document exactly where you need it.
- **Highlight and Comment:** Mark important text with semi-transparent highlights and attach detailed side-comments. Comments are automatically linked to their highlights and stay synchronized during edits.
- **Undo / Redo:** Full session history tracking for all actions. Revert or re-apply changes (moving, scaling, coloring, adding/deleting) with ease (up to 254 steps).
- **True Vector Saves:** All modified elements and freehand drawings are written directly into the PDF backend as true vector drawings or native text objects using PyMuPDF – keeping your documents crisp and lightweight.
- **Lossless Edits:** The application safely embeds your session state inside the PDF file itself. Whenever you re-open a modified PDF in the editor, all your added and edited elements remain fully selectable and interactive.

## Requirements

The app runs on Python 3.10+ and requires the following libraries:
- `PyQt6` (for the graphical user interface)
- `PyMuPDF` (for the deep PDF backend manipulation)
- `pyinstaller` (only needed if you wish to compile standalone executables)

## Building from Source

We provide fully automated build scripts for Windows, macOS, and Linux that will automatically create an isolated environment, install the necessary dependencies, and package the application into a single executable file.

### Windows
1. Open PowerShell.
2. Run the build script:
   ```powershell
   .\build.ps1
   ```
3. You will find your standalone `PDF Editor.exe` in the newly created `dist/` directory.

### macOS / Linux
1. Open your Terminal.
2. Make the script executable:
   ```bash
   chmod +x build.sh
   ```
3. Run the script:
   ```bash
   ./build.sh
   ```
4. You will find your executable (or `.app` bundle on Mac) in the `dist/` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
