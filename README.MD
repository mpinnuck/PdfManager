# PDF Manager

Desktop Python app to load, reorder, preview, and merge PDF files.

## Features

- Add multiple PDFs and reorder them with drag and drop
- Left thumbnail panel with compact document cards
- Right in-app PDF preview panel
- Page-by-page preview scrolling with mouse wheel and scrollbar
- Merge to a new output PDF
- Output preview popup window (inside the app) with page navigation
- Session persistence for input files and last output path
- Window is resizable and centered on startup

## Requirements

- Python 3.10+
- macOS or Windows

## Installation

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Activate it:

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python pdfmanager.py
```

## How to Use

1. Click Add PDFs to select input files.
2. Drag cards in the left panel to set merge order.
3. Click a card and use the right preview panel to inspect pages.
4. Click Save As to create the merged PDF.
5. Use Output Preview to view the merged result in an in-app popup.

## Session and Config Storage

The app stores config and session data in the user config area:

- macOS: `~/Library/Application Support/PdfManager/config.json`
- Windows: `%APPDATA%/PdfManager/config.json`
- Linux: `$XDG_CONFIG_HOME/PdfManager/config.json` (or `~/.config/PdfManager/config.json`)

Persisted values include:

- Window geometry
- Last used folder
- Current input file list
- Last output PDF path

## Build Executable (PyInstaller)

Install PyInstaller if needed:

```bash
pip install pyinstaller
```

Build using the project spec file (recommended):

```bash
python -m PyInstaller --noconfirm pdfmanager.spec
```

Build output is generated in the `dist` folder.

On macOS, copy the app bundle to Applications:

```bash
cp -R dist/pdfmanager.app /Applications/
```

## Project Structure

```text
config.py
pdfmanager.py
requirements.txt
models/
services/
viewmodels/
views/
```
