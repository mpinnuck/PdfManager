# PDF Manager

Desktop Python app to load, reorder, preview, and merge PDF files.

## Features

- Add multiple PDFs and reorder their pages as thumbnail tiles
- Click, Shift-click, or Command/Ctrl-click to select one or more page tiles
- Drag selected page tile(s) to any position in the list to reorder them
- Right-click selected page(s) to delete them from the merge via a context menu
- Remove a source PDF from the page list
- Right in-app PDF preview panel
- Page-by-page preview scrolling with mouse wheel and scrollbar
- Click the preview to zoom in centered on the cursor; right-click to zoom
  back out; drag to pan while zoomed (view-only, doesn't affect the merged PDF)
- Merge to a new output PDF
- Output preview popup window (inside the app) with page navigation
- Session persistence for input files, page order, and last output path
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
2. Each page appears as a thumbnail tile in the left list, in merge order.
3. Click a tile to select it and preview it on the right. Shift-click or
   Command/Ctrl-click to select additional tiles.
4. Drag the selected tile(s) to a new position in the list; they drop where
   you release the mouse.
5. Right-click a tile to delete the selected page(s) via the context menu.
6. In the preview panel, click to zoom in on the cursor, right-click to zoom
   out, and drag to pan while zoomed in — this only changes what you see,
   not the merged output.
7. Click Save As to create the merged PDF.
8. Use Output Preview to view the merged result in an in-app popup.

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
