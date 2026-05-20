# User Guide

This guide covers internal behaviors and details that are not immediately obvious from the editor's UI.

## Table of Contents

- [Orientation](#orientation)
  - [The Three Tabs](#the-three-tabs)
  - [HWL Version Detection](#hwl-version-detection)
  - [Bank Names](#bank-names)
  - [Sample Type Classification](#sample-type-classification)
  - [SPU Address Table](#spu-address-table)
    - [How SPU Indices Are Assigned](#how-spu-indices-are-assigned)
    - [VAG Sample Rate Persistence](#vag-sample-rate-persistence)
    - [Important Considerations](#important-considerations)
- [General UI Behaviors](#general-ui-behaviors)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [Drag-and-Drop File Import](#drag-and-drop-file-import)
  - [Search / Filter](#search--filter)
  - [Undo / Redo](#undo--redo)
- [Listening and Inspecting](#listening-and-inspecting)
  - [Audio Playback](#audio-playback)
    - [Sample Playback](#sample-playback)
    - [FX Playback](#fx-playback)
    - [Low-Rate Sample Resampling](#low-rate-sample-resampling)
    - [Sequence Playback](#sequence-playback)
    - [Playback Accuracy](#playback-accuracy)
    - [Playback Limitations](#playback-limitations)
    - [Audio Cache](#audio-cache)
  - [Waveform Preview](#waveform-preview)
- [Bank and Sample Workflows](#bank-and-sample-workflows)
  - [Reordering Banks and Songs](#reordering-banks-and-songs)
  - [Copying Samples and Sequences](#copying-samples-and-sequences)
  - [Bank Merging](#bank-merging)
- [Music Production Workflows](#music-production-workflows)
  - [Music Workshop](#music-workshop)
    - [Editing Instruments and Percussion](#editing-instruments-and-percussion)
    - [Retargeting a Sample](#retargeting-a-sample)
    - [Inspecting Track Events](#inspecting-track-events)
    - [Replacing One Track from MIDI](#replacing-one-track-from-midi)
  - [MIDI to CSEQ Conversion](#midi-to-cseq-conversion)
    - [Standalone vs HWL](#standalone-vs-hwl)
  - [CSEQ to MIDI Export](#cseq-to-midi-export)
  - [MIDI Export Options](#midi-export-options)
  - [VAG Export Sample Rate](#vag-export-sample-rate)
  - [SFZ Export](#sfz-export)
- [Validation and Bulk Operations](#validation-and-bulk-operations)
  - [Bank / CSEQ Validation](#bank--cseq-validation)
  - [Batch Export](#batch-export)
  - [Saphi Audio Container (.sca)](#saphi-audio-container-sca)
    - [Export Saphi Audio Container](#export-saphi-audio-container)
    - [Import Saphi Audio Container](#import-saphi-audio-container)

## Orientation

### The Three Tabs

The editor is split into three tabs aimed at three personas. The same underlying handlers back every action, so the only difference between tabs is what's exposed and how it's framed.

- **Category Browser** — goal-oriented entry points framed in in-game terms (tracks, characters, menus, Adventure Hub). Each card drills into the bundle of audio for one in-game thing, with Play / Replace / Copy / Remove on each leaf. No structural operations live here (no Move Up/Down, no merging, no container removal) — for those go to the File Browser.
- **Music Workshop** — song-centric view aimed at composers and remixers. Shows a song's BPM / ticks-per-quarter / track count up top, plus full instrument and percussion tables with per-row Play and Actions controls. The waveform + transport dock stays pinned at the bottom of the tab. MIDI / SFZ export, MIDI track replacement, and per-instrument editing live here.
- **File Browser** — raw structural view of the HOWL file. Banks, songs, sequences, samples, FX tables, and the SPU address table all appear under a filterable tree. Move Up/Down, drag-reorder, Add/Replace/Remove of containers, Merge Bank, and Build Bank from VAGs all live here.

The Tools menu (Convert MIDI → CSEQ, Validate, Saphi import/export, Clear Audio Cache, VAG export sample rate) is cross-cutting and reachable from any tab.

### HWL Version Detection

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

### Bank Names

Banks and songs from an unmodified NTSC-U KART.HWL are labeled with their original purpose (e.g., "Dingo Canyon", "Character: Crash", "Boss Race"). These names are based on the index position in the file:

- **Banks 0-70**: Original NTSC-U banks with known names
- **Banks 71+**: Labeled as "Custom" (added by mods)
- **Songs 0-32**: Original NTSC-U songs with known names
- **Songs 33+**: Labeled as "Custom"

The names are for display only and are not stored in the HWL file. If you rearrange banks or songs, the names will no longer match the actual content.

### Sample Type Classification

The editor automatically classifies each SPU sample based on where it's referenced:

- **Instrument** - Referenced by a CSEQ instrument definition (melodic samples)
- **Percussion** - Referenced by a CSEQ percussion definition (drum samples)
- **SoundEffect** - Referenced by an OtherFX table entry

A sample can have multiple types (e.g., both Instrument and SoundEffect). The classification is recomputed each time the tree is rebuilt.

### SPU Address Table

The SPU Address Table is the global registry of all audio samples in the HWL file. Each entry has two fields:

- **spuAddr** - The SPU RAM address where the sample will be loaded at runtime (always 0 in the file, assigned by the game during bank loading)
- **spuSize** - The sample data size in 8-byte units (multiply by 8 for the actual byte count)

The **index** of an entry in this table is the sample's global ID. All banks, instruments, and sound effects reference samples by this index.

#### How SPU Indices Are Assigned

When you add a new sample to a bank or build a bank from VAG files, the editor automatically assigns SPU indices:

- **Build bank from VAGs**: New entries are appended to the end of the SPU table. If the table currently has 528 entries, the first new sample gets index 528, the next 529, etc.
- **Add sample to bank**: A new entry is appended to the end of the SPU table with the sample's size.
- **Replace sample**: The existing SPU index is kept, but the size entry is updated to match the new data.
- **Remove sample**: The sample is removed from the bank, but the SPU table entry is **not** deleted (removing it would shift all subsequent indices and break references in other banks and CSEQ files).

#### VAG Sample Rate Persistence

The HWL format has no per-sample rate field — playback rate is derived from whichever OtherFX entry, EngineFX entry, or CSEQ instrument references the sample. To keep an imported VAG's header `sample_rate` from being lost on save / reopen, the editor writes it into the FX table on every VAG-import path:

- **Existing OtherFX entries** that reference the affected SPU index have their `pitch` field updated to match the imported VAG.
- **Replace Sample** stops there — if no FX entry references the sample, nothing changes.
- **Add Sample / Build Bank from VAGs / drag-and-drop** of a brand-new sample with no existing FX reference will **auto-create** an OtherFX entry pointing at the new SPU index with `pitch` from the VAG header. You'll see this new entry under the Effects node in the tree.

If you don't want an auto-created Effects entry (e.g., the sample is purely a music note that you'll wire into a CSEQ instrument instead), just delete it from the tree — its sole purpose was to remember the rate.

#### Important Considerations

- SPU indices are global across the entire HWL file. If two banks reference the same SPU index, they share the same sample data.
- Changing a sample's data in one bank affects playback in any other bank that references the same SPU index.
- The SPU table can have gaps (unused entries). The game skips entries with spuSize = 0.

## General UI Behaviors

### Keyboard Shortcuts

Beyond the standard menu shortcuts (Ctrl+N/O/S/W/Q), the editor supports:

- **Space** — toggle play/stop for the selected item
- **Enter** — play the selected item
- **Delete** — remove the selected bank, song, sample, or sequence (with confirmation)
- **F5** — refresh the tree

### Drag-and-Drop File Import

Files can be dropped directly onto the editor window:

- **.hwl** — opens the file (replaces the current one, with unsaved-changes prompt)
- **.bnk** — adds as a new bank (requires an open HWL)
- **.cseq** — adds as a new song (requires an open HWL)
- **.vag** — adds as a sample to the currently selected bank, or bank 0 if no bank is selected

### Search / Filter

The filter bar matches against both tree columns (name and info text), case-insensitive. When a parent node matches (e.g., a bank name like "Dingo Canyon"), all its children are shown and the node auto-expands so you can see the samples inside. When only children match, the parent stays visible to provide context. Clearing the filter restores the tree to its exact pre-filter expanded/collapsed state.

### Undo / Redo

Most destructive operations can be undone with **Ctrl+Z** and redone with **Ctrl+Shift+Z** (or Ctrl+Y). This covers: removing/replacing banks, songs, samples, and sequences, as well as reordering via Move Up/Down and drag-and-drop. Adding a bank or song is not undoable (use remove to reverse it). The undo stack is cleared when you open, create, or close a file.

## Listening and Inspecting

### Audio Playback

#### Sample Playback

Clicking a sample in the tree decodes the VAG ADPCM data to PCM and plays it. The editor automatically looks up the correct playback pitch by checking the OtherFX table, EngineFX table, and CSEQ instrument/percussion definitions (in that order). If the sample isn't referenced anywhere, it falls back to 11025 Hz. Imported VAGs preserve their header's sample rate by populating an OtherFX entry — see [VAG Sample Rate Persistence](#vag-sample-rate-persistence). The [waveform preview](#waveform-preview) shows the decoded waveform with the loop point marked.

#### FX Playback

Selecting an OtherFX or EngineFX entry shows the waveform of its referenced SPU sample (with loop marker). Clicking the entry plays it at the entry's native pitch. The pitch is converted from the internal encoding: `Hz = (pitch / 4096) * 44100`.

#### Low-Rate Sample Resampling

Some media backends silently refuses to play WAVs whose sample rate falls below roughly 8 kHz (and above 48 kHz). Several stock CTR FX entries store pitch values that translate to sub-8 kHz rates — without intervention, clicking them would just produce silence even though the underlying VAG data is fine.

When the editor detects that a sample's intended rate falls outside this playable window, it:

1. Decodes the VAG to PCM at the original rate.
2. Linearly resamples the PCM to a backend-friendly rate (11025 Hz).
3. Writes a WAV at the new rate.

The audible pitch is preserved — only the encoding rate changes. The status bar shows a `— resampled <orig>→11025 Hz` suffix on the "Playing …" message so it's visible when this fallback kicks in. Exported WAVs are unaffected; they continue to be written at the decoder's default rate.

#### Sequence Playback

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

#### Playback Accuracy

The editor's playback uses lookup tables and volume formulas extracted from the decompiled CTR source code. The following aspects match the in-game behavior:

- **Pitch calculation**: Uses the exact 108-entry note frequency table from CTR for semitone-accurate pitch. Pitch bend (opcode 0x0A) applies both coarse (semitone shift) and fine (distortion constant) modulation, matching the game's `DECOMP_howl_InstrumentPitch` function.
- **Volume chain**: Applies the full CTR volume cascade: `(masterVol * songVol * seqVol) >> 10 * instVol * noteVel >> 15`, clamped to the SPU's 14-bit maximum.
- **Stereo panning**: Uses the 256-entry `volumeLR` lookup table from CTR (0=full left, 128=center, 255=full right) instead of linear interpolation.
- **Drum indexing**: Percussion tracks use the MIDI note number as the percussion table index (matching CTR opcode 0x05 for drum tracks), not the CHANGE_PATCH value.
- **Mid-note updates**: VELOCITY (opcode 0x06) and PAN (opcode 0x07) events update all currently playing voices on the sequence, matching CTR's `DECOMP_cseq_opcode_from06and07`. PITCH_BEND (opcode 0x0A) similarly updates active voice pitches.
- **Percussion ADSR**: Uses the CTR default drum ADSR values (ad=0x80FF, sr=0x1FC2): instant attack, full sustain hold, fast release.

#### Playback Limitations

Some differences remain compared to in-game audio:

- **ADSR envelope approximation**: The PS1 SPU processes ADSR envelopes in hardware with cycle-accurate timing. The editor approximates these timings in software, so attack/decay/release curves may not match exactly. The overall shape is correct but fine timing details differ.
- **No reverb**: The PS1 SPU has built-in hardware reverb with multiple modes (studio, hall, etc.). The editor does not simulate reverb, so songs that rely heavily on it (especially indoor/cave tracks) will sound drier than in-game.
- **Sample rate**: Songs are rendered at 22050 Hz rather than the PS1's native 44100 Hz. This reduces rendering time but may affect the character of high-frequency content.

The playback is suitable for previewing songs, verifying note arrangements, and checking that the correct samples are referenced.

#### Audio Cache

Decoded audio is cached in `%TEMP%/howl-editor/` (or the platform equivalent) using an MD5 checksum of the WAV data as the filename. Clicking the same sample or sequence again plays the cached file instantly without re-decoding.

To clear the cache, use **Tools > Clear Audio Cache**.

### Waveform Preview

The waveform appears for all audio types. Samples and FX entries show the waveform immediately on selection (before playing); sequences show it after rendering completes. The orange dashed vertical line marks the sample's **loop start point** — this is where the PS1 SPU jumps back to when it reaches the end of the sample data. Samples without a loop point have no marker and stop playing when the data ends. For rendered sequences, the stereo output is mixed to mono for display and no loop marker is shown.

## Bank and Sample Workflows

### Reordering Banks and Songs

Banks, songs, and sequences can be reordered via right-click **Move Up** / **Move Down** or by drag-and-drop within the tree.

Bank and song names are tied to index positions, not to the data (see [Bank Names](#bank-names)). Moving bank 0 ("SFX") to position 5 means the label "SFX" will appear on whatever bank now occupies index 0, not on the moved bank.

### Copying Samples and Sequences

The Actions menu on a sample leaf (category view) and the right-click menu on a sample row (file browser) both expose **Copy to Bank…**. A matching **Copy to Song…** is available on sequence leaves. Both flows open the same picker:

- **Target container** — pick the destination bank (for samples) or song (for sequences). Stock entries are labeled `Bank N — Name` / `Song N — Name`.
- **Target child** — either `(Append as new …)` to add a new slot, or one of the existing samples/sequences in the chosen container to replace it.

Append semantics:

- **Sample append** — the sample bytes are duplicated and a new SPU index is appended for the target bank. The source bank is untouched; the two copies are independent afterward.
- **Sequence append** — the source sequence is appended to the target song's CSEQ. Tempo, tracks, and events are preserved verbatim.

Replace semantics:

- **Sample replace** — the target slot's existing SPU index is kept, but its data is overwritten with the source sample's bytes. Anything else that references that SPU index will also play the new data. A size-change confirmation appears when the new bytes differ in size from the original, identical to the regular Replace flow.
- **Sequence replace** — the target song's sequence at the chosen slot is overwritten with the source sequence.

Both flows are undoable.

The file browser also has **Add Sequence (.cseq)…** on song right-click — picks an external `.cseq` file (prompting for a sub-song if the source has more than one) and appends it to the selected song.

### Bank Merging

The merge dialog lets you combine samples from two banks:

- **Source panel** (left): Shows samples available from the source bank
- **Result panel** (right): Shows the final merged bank, starting with the target bank's samples
- **Add**: Copy selected source samples into the result
- **Replace**: Swap a result entry with a source entry (1:1)
- **Remove**: Delete entries from the result
- **Move Up/Down** or **drag-and-drop**: Reorder samples in the result

The order of samples in the result determines the order in the bank blob. This matters because some CSEQ files may reference samples by their position within a bank.

## Music Production Workflows

### Music Workshop

The Music Workshop tab is a two-pane song-centric view. The left pane lists every song in the file; the right pane shows the selected song's musical anatomy.

The detail panel is organized top-to-bottom as:

1. **Title** — song index + stock name.
2. **Stats strip** — six cards: Tempo (BPM), Resolution (TPQN), Tracks (with drum-track indices as a hint), Sequences, Instruments, Percussion.
3. **Song actions** — Replace song · Export as MIDI.
4. **Sequences table** — one row per sub-sequence (Adventure Hub style multi-sequence songs have several; most songs have one). Each row shows # / BPM / track count / drum-track indices and exposes a ▶️ Play button plus a ⚙️ Actions menu with Replace · Copy to song · Export as MIDI · Inspect events · Remove.
5. **Instruments table** — one row per melodic instrument. Columns: index, sample SPU, source bank, pitch (Hz with note name + cents), volume, ADSR (read-only). Each row has ▶️ Play and ⚙️ Actions.
6. **Percussion table** — one row per percussion slot. Columns: MIDI note, GM drum name (Kick / Snare / etc.), sample SPU, source bank, pitch. Same ▶️ + ⚙️ pattern.

At the bottom of the tab a docked waveform + transport bar shows whatever's currently playing.

#### Editing Instruments and Percussion

The ⚙️ menu on each instrument or percussion row has an **Edit volume / pitch…** entry. The dialog lets you change two fields:

- **Volume** (0–255) — the per-entry mix level baked into the instrument table.
- **Pitch register** (0–0xFFFF) — the raw frequency value the SPU uses; a live `≈ Hz` readout shows you what audible rate it maps to (0x1000 = 44100 Hz native rate).

ADSR is intentionally not editable here — the bit-packed envelope shifts are easier to break than to tune, and CTR percussion uses a fixed default envelope anyway. Edits are undoable.

#### Retargeting a Sample

The ⚙️ menu also has **Point at another sample…** which opens a filterable list of every SPU index in the file (annotated with source bank + size). Picking one rewires that instrument or percussion entry to play a different sample, without exporting or reimporting any VAGs. Just changes the `sample_id` field on the entry and rewrites the CSEQ blob.

This is the fastest way to do things like "make Coco Park's lead synth use Crash Cove's lead synth sample" or "swap a kick drum for a different bank's kick."

#### Inspecting Track Events

The ⚙️ menu on each Sequences-table row has **Inspect events**, which opens a master-detail viewer:

- Left list: every track in the sub-sequence, labeled `Track N · drum/melodic · K events`.
- Right table: the selected track's raw `CseqEvent` stream — delta time, event type (NOTE_ON, NOTE_OFF, VELOCITY, PAN, CHANGE_PATCH, PITCH_BEND), and parameters annotated by event type.

This is useful when debugging an imported MIDI ("why is this track empty?") or just understanding what a CSEQ track actually looks like at the byte level.

#### Replacing One Track from MIDI

Inside the **Inspect events** dialog there's a **🎼 Replace selected track from MIDI…** button. Pick the track on the left, click the button, and you can pick a MIDI file (and a track inside it if there's more than one) whose events will overwrite the CSEQ track you had selected. The track's flags (drum/melodic) and instrument binding stay put — only the event stream changes.

MIDI pitches pass through unchanged; for drum tracks this means the MIDI's note numbers must already match your percussion table indices (otherwise the wrong drum slots will fire). For melodic tracks this is rarely an issue.

### MIDI to CSEQ Conversion

When converting a MIDI file to CSEQ:

- Each MIDI track with note events becomes a CSEQ track
- You must manually map each track to an SPU sample ID and set the playback frequency
- **Frequency encoding**: The internal format uses 4096 as a base for 44100 Hz. The dialog accepts Hz and converts automatically.
- **Drum tracks**: Check the "Drum?" checkbox for percussion tracks. These use the percussion instrument table instead of the melodic instrument table.
- The conversion preserves: note on/off, velocity, pan, pitch bend, program change, and tempo

#### Standalone vs HWL

If a HWL file is loaded, you'll be asked whether to add the result to the HWL or save as a standalone `.cseq` file. Without a HWL loaded, you can only save standalone.

The same applies to "Build Bank from VAGs" - it can produce a standalone `.bnk` file or add directly to the loaded HWL.

### CSEQ to MIDI Export

When exporting a song as MIDI:

- Each CSEQ track becomes a MIDI track
- **Drum tracks** (flag bit 0 set) are routed to MIDI channel 10 (the standard drum channel)
- **Melodic tracks** are assigned channels 1-9 and 11-16, skipping channel 10
- A tempo track is added with the song's BPM
- TPQN (ticks per quarter note) is preserved as the MIDI ticks_per_beat
- If a song has multiple sequences, exporting at the song level creates one MIDI file per sequence (suffixed `_seq0`, `_seq1`, etc.)

### MIDI Export Options

Every MIDI export (song or per-sequence) shows an options dialog. Two toggles:

- **Include in-song volume changes (CC#7)** — default on. Mid-song VELOCITY events are emitted as MIDI CC#7 volume changes so a DAW reproduces CTR's volume curves. Turn off if you want only raw note velocities (CTR-tools called this `IgnoreVolume`). When off, the delta-time of each dropped event is carried into the next emitted message so following notes stay aligned.
- **Apply each track's instrument volume at start** — default off. When on, each melodic track gets a CC#7 volume at tick 0 derived from the instrument it's bound to (CTR-tools called this `UseSampleVolumeForTracks`). Drum tracks are skipped because they aren't tied to a single instrument.

The dialog remembers your choices for the rest of the session — handy when batch-exporting many songs in a row.

### VAG Export Sample Rate

Under **Tools → VAG export sample rate** you can pick the default Hz value used when decoding VAG bytes to WAV for export. The HWL format doesn't store a per-sample rate (playback is derived from FX / instrument entries), so when exporting a raw sample to WAV the editor has to pick one. Choices: **11025**, **22050**, **33075**, **44100**. The selection persists across restarts via `QSettings`.

Affects: Export Sample as WAV, Export Bank Samples as WAVs, Batch Export's sample WAVs, and the SFZ exporter's WAV writes. Does **not** affect in-editor playback (which uses the FX-table-derived rate, falling back to 11025 only when no reference exists).

### SFZ Export

When exporting a song, the format picker now offers `.sfz` alongside `.cseq` and `.mid`. Choosing SFZ creates a sampler patch loadable in any SFZ-compatible host (sforzando, sfizz, etc.):

```
my_song.sfz
samples/
    SPU_0005.wav
    SPU_0006.wav
    ...
```

The text manifest contains one `<region>` per instrument and percussion entry pointing at the appropriate WAV:

- **Melodic instruments** get `pitch_keycenter=60` plus an optional `tune=<cents>` derived from the instrument's frequency register (so an `0x2000` instrument shifts up exactly one octave) and a `volume` field in dB derived from the volume byte.
- **Percussion** entries get `key=<N>` (the MIDI note number that triggers them) plus the same tune / volume mapping.

Samples are deduplicated by SPU index — if two instruments reference the same sample, the WAV is written once. The WAV encoding rate is whatever you've set under [VAG Export Sample Rate](#vag-export-sample-rate).

## Validation and Bulk Operations

### Bank / CSEQ Validation

The validation tool (Tools > Validate Bank / Song) checks whether a bank contains all the SPU sample IDs that a CSEQ song needs. It reports:

- How many of the required samples are present
- A list of every missing SPU index

Note that in the actual game, multiple banks are loaded simultaneously (SFX bank + level bank + character banks). A single bank not passing validation doesn't necessarily mean the song won't play - the missing samples may be provided by another bank loaded at runtime. See the [audio loading documentation](audio-loading.md) for details on which banks the game loads together.

### Batch Export

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

### Saphi Audio Container (.sca)

The Saphi Audio Container (`.sca`) bundles a single bank + song pair into one file that the Saphi runtime streams into PS1 memory at level-load time, replacing the original music without modifying the KART.HWL. See [sca.md](formats/sca.md) for the wire format.

#### Export Saphi Audio Container

**Tools > Export Saphi Audio Container...** prompts you to pick one bank and one song from the loaded HWL, plus a track name and author. The editor writes:

- The full bank blob (header + padded sample data), capped at `0x64000` bytes
- The full CSEQ blob, capped at `0xC000` bytes
- A per-sample `spuSize` array extracted from the loaded HWL's SPU Address Table (in bank-header order) — this lets the Saphi runtime use the source HWL's sizes even when they differ from the player's ISO HOWL
- A small UTF-8 JSON metadata chunk with `name` and `author`

The dialog warns if the selected bank exceeds the Saphi size cap. Bank/song pairing is not validated at export — use [Tools > Validate Bank/Song](#bank--cseq-validation) first if you want to confirm the bank contains every sample the CSEQ references.

#### Import Saphi Audio Container

**Tools > Import Saphi Audio Container...** is the inverse: pick a `.sca` file and the editor appends its bank and CSEQ as new entries on the loaded HWL (the SIZE chunk is ignored on import because the loaded HWL already has authoritative SPU sizes). A status-bar message reports the imported track's name, author, and the new bank/song indices.

Unknown chunks in the container are skipped silently for forward compatibility, so newer `.sca` files with extra metadata still import cleanly.
