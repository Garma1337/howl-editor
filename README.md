# HOWL Editor

A graphical editor for CTR (Crash Team Racing) `.HWL` sound files. Create, inspect, and modify HOWL files containing sound banks (SPU sample collections) and songs (CSEQ sequences).

## Features

### File Operations

- **Create, open, close, save** HWL files
- **Batch export** entire HWL to organized folders (`banks/`, `songs/`, `samples/instruments/`, `samples/percussion/`, `samples/effects/`) with VAG + WAV + MIDI

### Banks

- **Add, replace, remove** banks
- **Merge banks** - combine samples from two banks with drag-and-drop reordering
- **Build banks** from multiple `.vag` files (standalone or add to HWL)
- **Export** banks as `.bnk`, samples as `.vag` or `.wav`
- **Browse samples** in the tree view with SPU index, size, and type classification

### Songs & Sequences

- **Add, replace, remove** songs
- **Replace or remove** individual sequences within a song
- **Export** songs as `.cseq` or MIDI files (per-song or per-sequence)
- **Convert MIDI to CSEQ** with per-track instrument mapping (standalone or add to HWL)
- **Export Saphi Audio Container** (`.sca`) — bundle one bank + one song + per-sample SPU sizes + name/author metadata into a single file the Saphi runtime can stream into PS1 memory
- **Import Saphi Audio Container** — append a `.sca`'s bank and song to the loaded HWL

### Samples

- **Add, replace, remove** individual samples within a bank
- **Export** as `.vag` or `.wav`

### Audio Playback

- **Reasonably CTR-accurate rendering** - pitch, volume, panning, and drum indexing use lookup tables extracted from the decompiled CTR source code
- **Pitch bend** (opcode 0x0A), mid-note **volume** (0x06) and **pan** (0x07) changes applied in real time
- **Click to play** samples, sequences, OtherFX, and EngineFX entries
- **Player bar** with play/stop, seek slider, and elapsed/total time display
- **Automatic pitch detection** for bank samples - looks up the correct playback rate from FX and instrument tables
- **Audio cache** - decoded audio is cached in `%TEMP%/howl-editor/` for instant replay (clearable via Tools menu)

### Effects Tables

- **Browse OtherFX** entries (sound effects) with volume, pitch, duration, and SPU index
- **Browse EngineFX** entries (engine sounds) with volume, pitch, and SPU index
- **Click to play** any effect entry at its native pitch

### Waveform Preview

- **Waveform display** for samples and FX entries on selection (before playing), and for rendered sequences after playback
- **Loop start marker** shown as an orange dashed line on the waveform

### Editor

- **Drag-and-drop file import** - drop `.hwl`, `.bnk`, `.cseq`, or `.vag` files onto the window
- **Drag-and-drop reordering** of banks, songs, and sequences in the tree

### Analysis

- **Bank/CSEQ validation** - verify a bank contains all samples needed by a song, lists all missing sample IDs
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

PyInstaller is already in `requirements.txt`, so the setup step above installs it. To build:

```bash
pyinstaller HowlEditor.spec
```

The output is in `dist/HowlEditor/`. The spec trims unused PySide6 / Qt modules so the bundle stays small (Multimedia is kept for `QMediaPlayer`).

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
documentation/
    formats/            Format specifications (HOWL, CSEQ, Bank, VAG)
    audio-loading.md    Runtime audio loading system

howl_editor/
    core/               DI container, template engine, VLQ codec
    models/             Data models (HowlFile, CseqFile, VagSample, BankSample, BankBuildResult, ScaFile, ScaMetadata, ScaFormat)
    howl/               HWL reader, writer, editor, version detector
    cseq/               CSEQ reader, writer, editor
    vag/                VAG reader, writer
    bank/               Bank reader, builder
    midi/               MIDI to CSEQ converter and CSEQ to MIDI exporter
    sca/                Saphi Audio Container reader, writer, chunk iterator, metadata codec, sample-sizes extractor, size caps
    audio/
        settings/       PS1 hardware constants, CTR lookup tables
        decoder/        VAG ADPCM decoder, ADSR envelope decoder
        voice/          Voice playback, pitch calculator, gain calculator
        cseq_renderer   CSEQ sequence renderer
        sample_lookup   Sample data and pitch lookup across banks/FX/songs
        audio_player    Qt Multimedia playback with file caching
        wav_writer      PCM to WAV conversion
    analysis/           Sample classifier, bank/CSEQ validator
    export/             Batch exporter
    gui/
        detail/         Detail formatters (HOWL, FX, bank, song)
        templates/      HTML templates and CSS for detail panel
        dialog/         Dialogs (merge bank, convert MIDI, Saphi audio container export)
        handler/        Action handlers (bank, sample, song, playback, tools)
        widget/         Widgets (filter bar, player bar, waveform)
        command/        Undo commands (swap blob, remove item, move item/sequence)
        main_window.py  Main window shell
    services.py         Service registrations
```

## Documentation

- **[User Guide](documentation/user-guide.md)** - Non-obvious behaviors: undo/redo, keyboard shortcuts, drag-and-drop, sample pitch lookup, filter logic, waveform loop markers, reordering caveats, SPU index assignment, MIDI conversion, audio playback accuracy, bank merging, batch export, validation, Saphi container import/export
- **[Audio Loading](documentation/audio-loading.md)** - How CTR loads audio at runtime: level/character/boss bank selection, song mapping, loading pipeline

Format specifications:

- **[HOWL Format](documentation/formats/howl.md)** - Master audio container (.HWL), header structure, SPU address table, OtherFX/EngineFX definitions, bank/song offset tables
- **[CSEQ Format](documentation/formats/cseq.md)** - Music sequence format, instrument/percussion definitions, song structure, track events and opcodes, VLQ delta time encoding
- **[Bank Format](documentation/formats/bank.md)** - Sample bank structure, SPU memory management, runtime loading pipeline
- **[VAG Format](documentation/formats/vag.md)** - PlayStation ADPCM audio samples, header structure, frame encoding, decoding algorithm
- **[SCA Format](documentation/formats/sca.md)** - Saphi Audio Container, chunked bank + CSEQ + per-sample SPU sizes + metadata for runtime music override
