# HOWL Editor

A graphical editor for CTR (Crash Team Racing) `.HWL` sound files. Create, inspect, and modify HOWL files containing sound banks (SPU sample collections) and songs (CSEQ sequences).

## Features

### File Operations
- **Create, open, close, save** HWL files
- **HOWL version detection** - identifies release, prototype, and demo builds
- **Batch export** entire HWL to organized folders (`banks/`, `songs/`, `samples/instruments/`, `samples/percussion/`, `samples/effects/`) with VAG + WAV + MIDI

### Banks
- **Add, replace, remove** banks
- **Merge banks** - combine samples from two banks with reordering support
- **Build banks** from multiple `.vag` files (standalone or add to HWL)
- **Export** banks as `.bnk` or individual samples as `.vag` / `.wav`
- **Browse samples** in the tree view with SPU index, size, and type classification

### Songs & Sequences
- **Add, replace, remove** songs
- **Replace or remove** individual sequences within a song
- **Export** songs as `.cseq` or MIDI files
- **Convert MIDI to CSEQ** with per-track instrument mapping (standalone or add to HWL)

### Samples
- **Replace** individual samples within a bank
- **Export** as `.vag` or `.wav`
- **Sample type classification** - automatically tags samples as Instrument, Percussion, or SoundEffect
- **Click to play** any sample in the tree (requires Qt Multimedia)

### Audio Playback
- **Play samples** by clicking them in the tree
- **Play sequences** by clicking them in the tree (renders CSEQ to audio)
- **Stop** playback via toolbar button

### Analysis
- **Bank/CSEQ validation** - verify a bank contains all samples needed by a song
- **NTSC-U bank and song names** shown in tree view and detail panels (Custom label for modded entries)

## Requirements

- Python 3.11+
- PySide6
- mido (optional, for MIDI import/export)

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

Or as a module:

```bash
python -m howl_editor
```

## Building an Executable

```bash
pip install pyinstaller
pyinstaller HowlEditor.spec
```

The output is in `dist/HowlEditor/`.

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
documentation/
    formats/        Format specifications (HOWL, CSEQ, Bank, VAG)
    audio-loading.md  Runtime audio loading system

howl_editor/
    core/           DI container
    models/         Data models (HowlFile, CseqFile, VagSample, BankSample, ...)
    howl/           HWL reader, writer, editor, version detector
    cseq/           CSEQ reader, writer, editor
    vag/            VAG reader, writer
    bank/           Bank reader, builder
    midi/           MIDI to CSEQ converter and CSEQ to MIDI exporter
    audio/          VAG decoder, CSEQ renderer, audio player
    analysis/       Sample classifier, bank/CSEQ validator
    export/         Batch exporter
    gui/            PySide6 GUI
    services.py     Service registrations
    constants.py    Format constants and struct definitions
    vlq.py          Variable-length quantity codec

tests/              Mirrors the source structure
```

## Documentation

- **[Audio Loading](documentation/audio-loading.md)** - How CTR loads audio at runtime: level/character/boss bank selection, song mapping, loading pipeline

Format specifications:

- **[HOWL Format](documentation/formats/howl.md)** - Master audio container (.HWL), header structure, SPU address table, OtherFX/EngineFX definitions, bank/song offset tables
- **[CSEQ Format](documentation/formats/cseq.md)** - Music sequence format, instrument/percussion definitions, song structure, track events and opcodes, VLQ delta time encoding
- **[Bank Format](documentation/formats/bank.md)** - Sample bank structure, SPU memory management, runtime loading pipeline
- **[VAG Format](documentation/formats/vag.md)** - PlayStation ADPCM audio samples, header structure, frame encoding, decoding algorithm
