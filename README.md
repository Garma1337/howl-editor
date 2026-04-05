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
documentation/      Documentation files
    
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

## Format Documentation

Detailed format specifications are in the `documentation/` directory:

- **[HOWL Format](documentation/formats/howl.md)** - Master audio container (.HWL), header structure, SPU address table, OtherFX/EngineFX definitions, bank/song offset tables, runtime loading sequence
- **[CSEQ Format](documentation/formats/cseq.md)** - Music sequence format, instrument/percussion definitions, song structure, track events and opcodes, VLQ delta time encoding
- **[Bank Format](documentation/formats/bank.md)** - Sample bank structure, SPU memory management, runtime loading pipeline
- **[VAG Format](documentation/formats/vag.md)** - PlayStation ADPCM audio samples, header structure, frame encoding, decoding algorithm
- **[Audio Loading](documentation/formats/audio_loading.md)** - How CTR loads audio at runtime: level/character/boss bank selection, song mapping, loading pipeline
