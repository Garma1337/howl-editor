# HOWL Editor

A graphical editor for CTR (Crash Team Racing) `.HWL` sound files. Create, inspect, and modify HOWL files containing sound banks (SPU sample collections) and songs (CSEQ sequences).

The editor is organized into three tabs aimed at three personas:

- **Category Browser** — targeted edits framed in in-game terms (tracks, characters, menus). Best for "replace this track's music" or "swap a character's voice."
- **Music Workshop** — song-centric view with per-instrument editing, sample auditioning, MIDI / SFZ export, and MIDI track replacement. Best for composers and remixers.
- **File Browser** — raw structural editing of banks, songs, sequences, and samples. Best for modders and developers working on file layout.

## Features

### File Operations

- **Create, open, close, save** HWL files
- **Batch export** entire HWL to organized folders (`banks/`, `songs/`, `samples/instruments/`, `samples/percussion/`, `samples/effects/`) with VAG + WAV + MIDI

### Banks

- **Add, replace, remove** banks
- **Merge banks** - combine samples from two banks with drag-and-drop reordering
- **Build banks** from multiple `.vag` files (standalone or add to HWL)
- **Copy samples between banks** - append to another bank or replace an existing sample slot
- **Export** banks as `.bnk`, samples as `.vag` or `.wav`
- **Browse samples** in the tree view with SPU index, size, and type classification

### Songs & Sequences

- **Add, replace, remove** songs
- **Add, replace, remove** individual sequences within a song
- **Copy sequences between songs** - append to another song or replace an existing sequence slot
- **Export** songs as `.cseq`, MIDI, or **SFZ sampler patch** (text manifest + WAV samples folder, loadable in any SFZ-compatible DAW)
- **Replace one track's events** from a MIDI file without rewriting the whole sequence
- **Inspect raw CSEQ events** per track (delta time, event type, params) for debugging
- **Convert MIDI to CSEQ** with per-track instrument mapping (standalone or add to HWL)
- **Export Saphi Audio Container** (`.sca`) — bundle one bank + one song + per-sample SPU sizes + name/author metadata into a single file the Saphi runtime can stream into PS1 memory
- **Import Saphi Audio Container** — append a `.sca`'s bank and song to the loaded HWL

### Instruments & Percussion (Music Workshop)

- **Per-instrument editing** of volume and pitch (frequency register, with live ≈Hz readout)
- **Per-percussion editing** of volume and pitch
- **Retarget** an instrument or percussion entry at a different SPU sample without exporting / reimporting VAGs
- **Audition** any instrument or percussion sample directly from its row
- **GM drum names** shown for percussion entries

### Samples

- **Add, replace, remove** individual samples within a bank
- **Export** as `.vag` or `.wav`

### Audio Playback

- **Reasonably CTR-accurate rendering** - pitch, volume, panning, and drum indexing use lookup tables extracted from the decompiled CTR source code
- **Pitch bend** (opcode 0x0A), mid-note **volume** (0x06) and **pan** (0x07) changes applied in real time
- **Click to play** samples, sequences, OtherFX, and EngineFX entries
- **Player bar** with play/stop, seek slider, and elapsed/total time display
- **Automatic pitch detection** for bank samples - looks up the correct playback rate from FX and instrument tables
- **Low-rate sample resampling** - samples whose intended rate falls outside the audio backend's playable range are resampled to a safe rate while preserving audible pitch, instead of playing silently
- **Configurable VAG export sample rate** (11025 / 22050 / 33075 / 44100 Hz) used by all WAV-export paths
- **Audio cache** - decoded audio is cached in `%TEMP%/howl-editor/` for instant replay (clearable via File menu)

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
- **Diagnose HOWL File** - whole-file sweep for data the console can't load: songs over the song-buffer limit, level banks that overflow SPU sound memory, broken sample references, unreadable blobs, and a file grown past its disc slot
- **Engine-limit guards and warning icons** - edits that would exceed a hard console limit (song size, SPU residency, file size) warn before applying, and offending banks/songs/the file are marked with a ❌ / ⚠️ icon across the File Browser tree, Category Browser, and Music Workshop, with a banner explaining each one
- **Custom Mode** (Settings menu) - disables every engine-limit check and hides the status icons, for modded games where the stock limits no longer apply
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

## Documentation

- **[User Guide](documentation/user-guide.md)** - Non-obvious behaviors: tab roles, Music Workshop, instrument/percussion editing, SFZ export, MIDI export options, per-track MIDI replacement, configurable sample rate, undo/redo, keyboard shortcuts, drag-and-drop, sample pitch lookup, filter logic, waveform loop markers, reordering caveats, SPU index assignment, MIDI conversion, audio playback accuracy, bank merging, batch export, validation, Saphi container import/export
- **[Audio Loading](documentation/audio-loading.md)** - How CTR loads audio at runtime: level/character/boss bank selection, song mapping, loading pipeline

Format specifications:

- **[HOWL Format](documentation/formats/howl.md)** - Master audio container (.HWL), header structure, SPU address table, OtherFX/EngineFX definitions, bank/song offset tables
- **[CSEQ Format](documentation/formats/cseq.md)** - Music sequence format, instrument/percussion definitions, song structure, track events and opcodes, VLQ delta time encoding
- **[Bank Format](documentation/formats/bank.md)** - Sample bank structure, SPU memory management, runtime loading pipeline
- **[VAG Format](documentation/formats/vag.md)** - PlayStation ADPCM audio samples, header structure, frame encoding, decoding algorithm
- **[SCA Format](documentation/formats/sca.md)** - Saphi Audio Container, chunked bank + CSEQ + per-sample SPU sizes + metadata for runtime music override
