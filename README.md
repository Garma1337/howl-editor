# HOWL Editor

A graphical editor for CTR (Crash Team Racing) `.HWL` sound files. Create, inspect, and modify HOWL files containing sound banks (SPU sample collections) and songs (CSEQ sequences).

## Features

- **Create** new HWL files from scratch
- **Open and inspect** existing HWL files with a tree view showing banks, songs, SPU tables, and effects
- **Add, replace, and remove** banks and songs
- **Export** individual banks (`.bnk`) or their samples as `.vag` files via right-click context menu
- **Export** songs as `.cseq` files
- **Build banks** from multiple `.vag` files with automatic SPU address table management
- **Convert MIDI to CSEQ** with per-track instrument mapping (requires `mido`)

## Requirements

- Python 3.12+
- PySide6
- mido (optional, for MIDI conversion)

## Setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# or: source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Building an Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "HowlEditor" main.py
```

The output is in `dist/HowlEditor.exe`.

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
howl_editor/
    core/           Application Core
    models/         Pure data models (HowlFile, CseqFile, VagSample, BankSample, ...)
    howl/           HWL format reader, writer, and editor
    cseq/           CSEQ format reader and writer
    vag/            VAG format reader and writer
    bank/           Bank blob reader and builder
    midi/           MIDI to CSEQ converter and models
    gui/            PySide6 GUI (main window, detail panel, MIDI dialog)
    services.py     Default service registrations
    constants.py    Shared format constants and struct definitions
    vlq.py          Variable-length quantity codec

tests/              Mirrors the source structure
```

## HWL Format Overview

A `.HWL` (HOWL) file is the audio container used by CTR. It contains:

| Section | Description |
|---------|-------------|
| Header (40 bytes) | Magic (`HOWL`), version, table counts |
| SPU Address Table | Sample size entries (4 bytes each) |
| OtherFX Table | Sound effect definitions (8 bytes each) |
| EngineFX Table | Engine sound definitions (8 bytes each) |
| Bank Offsets | Sector offsets to bank data (2 bytes each) |
| Song Offsets | Sector offsets to song data (2 bytes each) |
| Bank Data | Sector-aligned sample collections |
| Song Data | Sector-aligned CSEQ sequences |

All data is sector-aligned (0x800 / 2048 bytes).

## Related Formats

- **CSEQ** - CTR's sequence format (similar to MIDI), contains instrument definitions and note/event data
- **VAG** - PlayStation ADPCM audio samples, 16 bytes per frame
- **Bank** - Header with sample indices + concatenated VAG data, loaded into SPU memory
