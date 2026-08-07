# Gemini AI Instructions for PDF Editor

## Global Directives
- **Executable Builds:** Whenever significant changes are made to the `main.py` application code (e.g., adding features, fixing bugs, UI updates), you MUST automatically run the `.\build.ps1` script at the end of the process to update the standalone executable in the `dist` folder.
- **Automated Build Numbering:** The app uses a `version.json` to track the build number. The `build.ps1` script must automatically increment this number by 1 and update the build year with every build.

## Memory
Always check and maintain the `memory.md` file to keep track of features, architecture decisions, and current project status.