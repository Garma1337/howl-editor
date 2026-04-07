# User Guide

This guide covers internal behaviors and details that are not immediately obvious from the editor's UI.

## Table of Contents

- [SPU Address Table](#spu-address-table)
  - [How SPU Indices Are Assigned](#how-spu-indices-are-assigned)
  - [Important Considerations](#important-considerations)
- [Bank Names](#bank-names)
- [Sample Type Classification](#sample-type-classification)
- [MIDI to CSEQ Conversion](#midi-to-cseq-conversion)
  - [Standalone vs HWL](#standalone-vs-hwl)
- [CSEQ to MIDI Export](#cseq-to-midi-export)
- [Audio Playback](#audio-playback)
  - [Sample Playback](#sample-playback)
  - [FX Playback](#fx-playback)
  - [Sequence Playback](#sequence-playback)
  - [Playback Accuracy](#playback-accuracy)
  - [Playback Limitations](#playback-limitations)
  - [Audio Cache](#audio-cache)
- [Bank Merging](#bank-merging)
- [Bank/CSEQ Validation](#bankcseq-validation)
- [Batch Export](#batch-export)
- [HWL Version Detection](#hwl-version-detection)

## SPU Address Table

The SPU Address Table is the global registry of all audio samples in the HWL file. Each entry has two fields:

- **spuAddr** - The SPU RAM address where the sample will be loaded at runtime (always 0 in the file, assigned by the game during bank loading)
- **spuSize** - The sample data size in 8-byte units (multiply by 8 for the actual byte count)

The **index** of an entry in this table is the sample's global ID. All banks, instruments, and sound effects reference samples by this index.

### How SPU Indices Are Assigned

When you add a new sample to a bank or build a bank from VAG files, the editor automatically assigns SPU indices:

- **Build bank from VAGs**: New entries are appended to the end of the SPU table. If the table currently has 528 entries, the first new sample gets index 528, the next 529, etc.
- **Add sample to bank**: A new entry is appended to the end of the SPU table with the sample's size.
- **Replace sample**: The existing SPU index is kept, but the size entry is updated to match the new data.
- **Remove sample**: The sample is removed from the bank, but the SPU table entry is **not** deleted (removing it would shift all subsequent indices and break references in other banks and CSEQ files).

### Important Considerations

- SPU indices are global across the entire HWL file. If two banks reference the same SPU index, they share the same sample data.
- Changing a sample's data in one bank affects playback in any other bank that references the same SPU index.
- The SPU table can have gaps (unused entries). The game skips entries with spuSize = 0.

## Bank Names

Banks and songs from an unmodified NTSC-U KART.HWL are labeled with their original purpose (e.g., "Dingo Canyon", "Character: Crash", "Boss Race"). These names are based on the index position in the file:

- **Banks 0-70**: Original NTSC-U banks with known names
- **Banks 71+**: Labeled as "Custom" (added by mods)
- **Songs 0-32**: Original NTSC-U songs with known names
- **Songs 33+**: Labeled as "Custom"

The names are for display only and are not stored in the HWL file. If you rearrange banks or songs, the names will no longer match the actual content.

## Sample Type Classification

The editor automatically classifies each SPU sample based on where it's referenced:

- **Instrument** - Referenced by a CSEQ instrument definition (melodic samples)
- **Percussion** - Referenced by a CSEQ percussion definition (drum samples)
- **SoundEffect** - Referenced by an OtherFX table entry

A sample can have multiple types (e.g., both Instrument and SoundEffect). The classification is recomputed each time the tree is rebuilt.

## MIDI to CSEQ Conversion

When converting a MIDI file to CSEQ:

- Each MIDI track with note events becomes a CSEQ track
- You must manually map each track to an SPU sample ID and set the playback frequency
- **Frequency encoding**: The internal format uses 4096 as a base for 44100 Hz. The dialog accepts Hz and converts automatically.
- **Drum tracks**: Check the "Drum?" checkbox for percussion tracks. These use the percussion instrument table instead of the melodic instrument table.
- The conversion preserves: note on/off, velocity, pan, pitch bend, program change, and tempo

### Standalone vs HWL

If a HWL file is loaded, you'll be asked whether to add the result to the HWL or save as a standalone `.cseq` file. Without a HWL loaded, you can only save standalone.

The same applies to "Build Bank from VAGs" - it can produce a standalone `.bnk` file or add directly to the loaded HWL.

## CSEQ to MIDI Export

When exporting a song as MIDI:

- Each CSEQ track becomes a MIDI track
- **Drum tracks** (flag bit 0 set) are routed to MIDI channel 10 (the standard drum channel)
- **Melodic tracks** are assigned channels 1-9 and 11-16, skipping channel 10
- A tempo track is added with the song's BPM
- TPQN (ticks per quarter note) is preserved as the MIDI ticks_per_beat
- If a song has multiple sequences, exporting at the song level creates one MIDI file per sequence (suffixed `_seq0`, `_seq1`, etc.)

## Audio Playback

### Sample Playback

Clicking a sample in the tree decodes the VAG ADPCM data to PCM and plays it at 11025 Hz (the default CTR sample rate).

### FX Playback

Clicking an OtherFX or EngineFX entry plays its referenced sample at the entry's native pitch. The pitch is converted from the internal encoding: `Hz = (pitch / 4096) * 44100`.

### Sequence Playback

Clicking a sequence renders the entire song offline before playing:

1. All instruments and percussions referenced by the CSEQ are collected
2. Their sample data is found by searching all banks in the HWL
3. Each note event decodes its sample, applies the ADSR envelope, and mixes at the correct pitch, volume, and pan
4. Melodic pitch is calculated using the CTR note frequency lookup table, matching the game's fixed-point pitch computation
5. Percussion uses the note number to select the drum instrument (matching CTR's drum indexing), with the instrument's fixed pitch
6. Volume is computed using the CTR volume chain: master music volume, song volume, sequence volume, instrument volume, and note velocity
7. Stereo panning uses the CTR volume lookup table for accurate L/R balance
8. Mid-note volume, pan, and pitch bend changes update already-playing voices in real time
9. The result is rendered at 22050 Hz stereo

Rendering can take a few seconds for complex songs.

### Playback Accuracy

The editor's playback uses lookup tables and volume formulas extracted from the decompiled CTR source code. The following aspects match the in-game behavior:

- **Pitch calculation**: Uses the exact 108-entry note frequency table from CTR for semitone-accurate pitch. Pitch bend (opcode 0x0A) applies both coarse (semitone shift) and fine (distortion constant) modulation, matching the game's `DECOMP_howl_InstrumentPitch` function.
- **Volume chain**: Applies the full CTR volume cascade: `(masterVol * songVol * seqVol) >> 10 * instVol * noteVel >> 15`, clamped to the SPU's 14-bit maximum.
- **Stereo panning**: Uses the 256-entry `volumeLR` lookup table from CTR (0=full left, 128=center, 255=full right) instead of linear interpolation.
- **Drum indexing**: Percussion tracks use the MIDI note number as the percussion table index (matching CTR opcode 0x05 for drum tracks), not the CHANGE_PATCH value.
- **Mid-note updates**: VELOCITY (opcode 0x06) and PAN (opcode 0x07) events update all currently playing voices on the sequence, matching CTR's `DECOMP_cseq_opcode_from06and07`. PITCH_BEND (opcode 0x0A) similarly updates active voice pitches.
- **Percussion ADSR**: Uses the CTR default drum ADSR values (ad=0x80FF, sr=0x1FC2): instant attack, full sustain hold, fast release.

### Playback Limitations

Despite the accuracy improvements, some differences remain compared to in-game audio:

- **ADSR envelope approximation**: The PS1 SPU processes ADSR envelopes in hardware with cycle-accurate timing. The editor approximates these timings in software, so attack/decay/release curves may not match exactly. The overall shape is correct but fine timing details differ.
- **No reverb**: The PS1 SPU has built-in hardware reverb with multiple modes (studio, hall, etc.). The editor does not simulate reverb, so songs that rely heavily on it (especially indoor/cave tracks) will sound drier than in-game.
- **Sample rate**: Songs are rendered at 22050 Hz rather than the PS1's native 44100 Hz. This reduces rendering time but may affect the character of high-frequency content.

The playback is suitable for previewing songs, verifying note arrangements, and checking that the correct samples are referenced.

### Audio Cache

Decoded audio is cached in `%TEMP%/howl-editor/` (or the platform equivalent) using an MD5 checksum of the WAV data as the filename. Clicking the same sample or sequence again plays the cached file instantly without re-decoding.

To clear the cache, use **Tools > Clear Audio Cache**.

## Bank Merging

The merge dialog lets you combine samples from two banks:

- **Source panel** (left): Shows samples available from the source bank
- **Result panel** (right): Shows the final merged bank, starting with the target bank's samples
- **Add**: Copy selected source samples into the result
- **Replace**: Swap a result entry with a source entry (1:1)
- **Remove**: Delete entries from the result
- **Move Up/Down** or **drag-and-drop**: Reorder samples in the result

The order of samples in the result determines the order in the bank blob. This matters because some CSEQ files may reference samples by their position within a bank.

## Bank/CSEQ Validation

The validation tool (Tools > Validate Bank/Song) checks whether a bank contains all the SPU sample IDs that a CSEQ song needs. It reports:

- How many of the required samples are present
- A list of every missing SPU index

Note that in the actual game, multiple banks are loaded simultaneously (SFX bank + level bank + character banks). A single bank not passing validation doesn't necessarily mean the song won't play - the missing samples may be provided by another bank loaded at runtime. See the [audio loading documentation](audio-loading.md) for details on which banks the game loads together.

## Batch Export

Batch export (File > Batch Export) creates an organized folder structure:

```
output/
    banks/
        bank_SFX_(universal).bnk
        bank_Dingo_Canyon.bnk
        ...
    songs/
        song_Dingo_Canyon.cseq
        song_Dingo_Canyon.mid       (if mido is installed)
        song_Dragon_Mines.cseq
        song_Dragon_Mines_seq0.mid  (multiple sequences = multiple MIDIs)
        song_Dragon_Mines_seq1.mid
        song_Dragon_Mines_seq2.mid
        ...
    samples/
        instruments/
            sample_015.vag
            sample_015.wav
            ...
        percussion/
            sample_072.vag
            sample_072.wav
            ...
        effects/
            sample_078.vag
            sample_078.wav
            ...
        other/
            sample_200.vag
            sample_200.wav
            ...
```

- Banks are exported as raw `.bnk` blobs
- Songs are exported as raw `.cseq` blobs plus MIDI conversions (one per sequence)
- Samples are deduplicated by SPU index and sorted into subfolders by type classification
- Both `.vag` (native PS1 format) and `.wav` (decoded PCM) are generated for each sample

## HWL Version Detection

The editor reads the version field from the HWL header and identifies known builds:

| Version | Build             |
|---------|-------------------|
| 0x6F    | Demo (Test Drive) |
| 0x71    | Demo (OPSM)       |
| 0x72    | Demo (Spyro)      |
| 0x78    | Beta (Aug 5)      |
| 0x7D    | Prototype         |
| 0x80    | Release           |

Modified HWL files are accepted as long as the HOWL magic (`0x4C574F48`) is valid. The version is displayed in the detail panel when the root node is selected.
