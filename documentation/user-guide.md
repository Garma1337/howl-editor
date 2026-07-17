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
  - [Replacing a Shared Sample](#replacing-a-shared-sample)
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
  - [Engine Limits and Warning Icons](#engine-limits-and-warning-icons)
  - [Diagnose HOWL File](#diagnose-howl-file)
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

The menu bar is cross-cutting and reachable from any tab:

- **File** — New / Open / Save / Save As, Recent Files, Batch Export, Clear Audio Cache.
- **Tools** — Build Bank from VAGs, Convert MIDI → CSEQ, Export / Import Saphi Audio Container.
- **Diagnose** — Validate Bank / Song, Diagnose HOWL File.
- **Settings** — Custom Mode, VAG export sample rate.

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
- **Replace sample**: The existing SPU index is kept, but the size entry is updated to match the new data. Because that entry is shared, replacing a sample other banks also claim needs care — see [Replacing a Shared Sample](#replacing-a-shared-sample).
- **Remove sample**: The sample is removed from the bank, but the SPU table entry is **not** deleted (removing it would shift all subsequent indices and break references in other banks and CSEQ files).

#### VAG Sample Rate Persistence

The HWL format has no per-sample rate field — playback rate is derived from whichever OtherFX entry, EngineFX entry, or CSEQ instrument references the sample. To keep an imported VAG's header `sample_rate` from being lost on save / reopen, the editor writes it into the FX table on every VAG-import path:

- **Existing OtherFX entries** that reference the affected SPU index have their `pitch` field updated to match the imported VAG.
- **Replace Sample** stops there — if no FX entry references the sample, nothing changes.
- **Add Sample / Build Bank from VAGs / drag-and-drop** of a brand-new sample with no existing FX reference will **auto-create** an OtherFX entry pointing at the new SPU index with `pitch` from the VAG header. You'll see this new entry under the Effects node in the tree.

If you don't want an auto-created Effects entry (e.g., the sample is purely a music note that you'll wire into a CSEQ instrument instead), just delete it from the tree — its sole purpose was to remember the rate.

#### Important Considerations

- SPU indices are global across the entire HWL file, and sharing is common — a universal effect can be claimed by thirty banks at once.
- **Each bank carries its own copy of a shared sample's bytes; only the index and the size entry are shared.** The two copies can even hold different audio. At runtime the game uploads a shared sample only once — whichever bank loads first wins — so the other copies are never heard.
- **Resizing a shared sample corrupts every other bank that claims it.** A bank blob is bare concatenated audio: the only thing marking where one sample ends and the next begins is that shared size entry. Give a sample a new length in one bank and the others still hold their old bytes while being read with the new size, so every sample from that one onward is cut at the wrong offset and plays as noise. Nothing errors — the file just quietly stops working, in a bank you never touched. See [Replacing a Shared Sample](#replacing-a-shared-sample).
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

To clear the cache, use **File > Clear Audio Cache**.

### Waveform Preview

The waveform appears for all audio types. Samples and FX entries show the waveform immediately on selection (before playing); sequences show it after rendering completes. The orange dashed vertical line marks the sample's **loop start point** — this is where the PS1 SPU jumps back to when it reaches the end of the sample data. Samples without a loop point have no marker and stop playing when the data ends. For rendered sequences, the stereo output is mixed to mono for display and no loop marker is shown.

## Bank and Sample Workflows

### Reordering Banks and Songs

Banks, songs, and sequences can be reordered via right-click **Move Up** / **Move Down** or by drag-and-drop within the tree.

Bank and song names are tied to index positions, not to the data (see [Bank Names](#bank-names)). Moving bank 0 ("SFX") to position 5 means the label "SFX" will appear on whatever bank now occupies index 0, not on the moved bank.

### Replacing a Shared Sample

Sample sizes live in one table keyed by SPU index and shared by every bank that claims that index, so replacing a sample with one of a **different length** rewrites a number the other banks are read with. They still hold their own, now-stale bytes, and get cut at the wrong offsets — see [Important Considerations](#important-considerations).

When this would happen, the editor names the banks and how many of their samples would break, and offers three choices:

- **Update all owning banks** — the replacement is written into every bank claiming that index, so the whole file stays coherent. This changes those banks' audio: they all end up playing the new sample. That is closer to what the console does anyway, since a shared index is only ever uploaded once. This is the safe default.
- **Only this bank** — writes just the bank you're editing and leaves the others mis-cut. Do this only if you intend to fix them yourself; they will be flagged with ❌ until you do.
- **Cancel** — abandon the replacement.

Either way it's one undo step: undoing puts every bank back.

Replacing a sample with one of **exactly the same length** never triggers this — the size entry doesn't move, so the other banks keep slicing correctly (they simply keep their own audio for that index).

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

1. **Title** — song index + stock name. When the song exceeds an engine limit, a warning banner appears directly under it (see [Engine Limits and Warning Icons](#engine-limits-and-warning-icons)).
2. **Stats strip** — six cards: Tempo (BPM), Resolution (TPQN), Tracks (with drum-track indices as a hint), Sequences, Instruments, Percussion.
3. **Sequences table** — one row per sub-sequence (Adventure Hub style multi-sequence songs have several; most songs have one). Each row shows # / BPM / track count / drum-track indices and exposes a ▶️ Play button plus a ⚙️ Actions menu with Replace · Copy to song · Export as MIDI · Inspect events · Remove. (Whole-song replace and export live in the File Browser.)
4. **Instruments table** — one row per melodic instrument. Columns: index, sample SPU, source bank, pitch (Hz with note name + cents), volume, ADSR (read-only). Each row has ▶️ Play and ⚙️ Actions.
5. **Percussion table** — one row per percussion slot. Columns: MIDI note, GM drum name (Kick / Snare / etc.), sample SPU, source bank, pitch. Same ▶️ + ⚙️ pattern.

At the bottom of the tab a docked waveform + transport bar shows whatever's currently playing.

#### Editing Instruments and Percussion

The ⚙️ menu on each instrument or percussion row has an **Edit volume / pitch…** entry. The dialog lets you change:

- **Volume** (0–255) — the per-entry mix level baked into the instrument / percussion table.
- **Pitch register** (0–0xFFFF) — the raw frequency value the SPU uses; a live `≈ Hz` readout shows you what audible rate it maps to (0x1000 = 44100 Hz native rate).
- **Attack/Decay (ADSR1)** and **Sustain/Release (ADSR2)** — *instruments only.* The two halves of the PS1 SPU's 32-bit ADSR register, shown as hex u16 values. ADSR1 packs attack mode/shift + decay shift + sustain level; ADSR2 packs sustain mode/direction/shift + release mode/shift. The fields are bit-packed and easy to break — when in doubt, copy the value from another instrument that envelopes the way you want, or keep the original. CTR percussion uses a fixed default envelope and has no per-entry ADSR slot, so those fields are not shown for percussion rows.

Edits are undoable.

#### Retargeting a Sample

The ⚙️ menu also has **Point at another sample…** which opens a filterable list of every SPU index in the file (annotated with source bank + size). Picking one rewires that instrument or percussion entry to play a different sample, without exporting or reimporting any VAGs. Select an entry and hit **▶️ Preview** to hear it first, so you can audition candidates before committing the change.

This is the fastest way to do things like "make Coco Park's lead synth use Crash Cove's lead synth sample" or "swap a kick drum for a different bank's kick."

> **⚠️ The chosen sample must belong to a bank the level actually loads.** Retargeting points the entry at a different sample; it does not copy that sample into the song's bank. In game, only the samples from the banks loaded for that level are available (the shared SFX bank + the level bank + the character banks). If you point at a sample that lives only in *another level's* bank, it plays **silence** in game — even though it auditions correctly in the editor.
>
> To reuse a sample from a bank the level doesn't load, first **Copy sample** (⚙️ on the sample row) into the level's own bank, *then* retarget the entry at that copy. To check what a level loads, see [Audio Loading](audio-loading.md); to confirm nothing is missing, run bank/CSEQ [validation](#bank--cseq-validation) against the level's bank.

#### Inspecting Track Events

The ⚙️ menu on each Sequences-table row has **Inspect events**, which opens a master-detail viewer:

- Left list: every track in the sub-sequence, labeled `Track N · drum/melodic · K events`.
- Right table: the selected track's raw `CseqEvent` stream — delta time, event type (NOTE_ON, NOTE_OFF, VELOCITY, PAN, CHANGE_PATCH, PITCH_BEND), and parameters annotated by event type.

This is useful when debugging an imported MIDI ("why is this track empty?") or just understanding what a CSEQ track actually looks like at the byte level.

#### Replacing One Track from MIDI

Inside the **Inspect events** dialog there's a **🎼 Replace selected track from MIDI…** button. Pick the track on the left, click the button, and you can pick a MIDI file (and a track inside it if there's more than one) whose events will overwrite the CSEQ track you had selected. The track's flags (drum/melodic) and instrument binding stay put — only the event stream changes.

MIDI pitches pass through unchanged; for drum tracks this means the MIDI's note numbers must already match your percussion table indices (otherwise the wrong drum slots will fire). For melodic tracks this is rarely an issue.

### MIDI to CSEQ Conversion

When converting a MIDI file to CSEQ, each MIDI track with note events becomes a CSEQ track. The conversion dialog is a table with one row per track (or per drum hit — see below) and columns **SPU Sample ID**, **Base pitch (note 60)**, and **Drum**.

**SPU + base pitch prefill.** The dialog prefills every sample ID and pitch so you can usually accept the defaults:

- If the song has a **paired bank** (converting/replacing in an HWL where the song maps to a known bank), the SPU column prefills from that bank's samples **in bank order** — so a MIDI laid out to mirror the bank maps across untouched. Otherwise it prefills sequentially (0, 1, 2, …) within the SPU range.
- The **Base pitch** column prefills from the pitch that sample is already played at elsewhere in the file — a value known to work. If you **change an SPU** to one with a known pitch, the column updates to match; if nothing references it, your entered value is left alone (and a brand-new sample falls back to 1024).
- The prefills are just defaults — override any cell before accepting.
- **Base pitch is not a sample rate.** It's the speed the sample plays at MIDI note 60: 4096 is 1.0×, halving drops an octave, doubling raises one. The value that sounds *right* depends on the musical pitch of the recording, which nothing in the file records — so there's no number that can be derived for you. Set it by ear. Entering your WAV's sample rate is the classic way to end up an octave or two out of tune. See [Pitch and Frequency](formats/cseq.md#pitch-and-frequency).

**Drum tracks.** Percussion on **MIDI channel 10** is auto-detected and expanded into **one row per unique drum hit**, each labeled with its GM drum name and needing its own SPU sample. If your percussion is on another channel, tick the **Drum** box on that track's row to expand it the same way.

You can spread percussion across **multiple** drum tracks — each unique drum hit across all of them maps to its own percussion slot.

The conversion preserves: note on/off, velocity, pan, pitch bend, program change, and tempo.

#### Replacing a Sequence Directly from MIDI

The Sequences table's ⚙️ **Replace** action (and drag-and-drop onto a sequence row) accepts a **MIDI file** as well as a `.cseq`. The file picker shows both types together by default, so you don't have to switch the type dropdown to reach a MIDI. Picking a MIDI opens the conversion dialog above and grafts the result into **just that one sequence** — the song's other sequences are left intact. This matters for songs 0–27, which carry the main track plus the Aku Aku / Uka Uka mask sequences: replacing the music leaves those masks untouched. (Picking a multi-sequence `.cseq` instead prompts for which sub-song to graft.) There's no need to convert the MIDI to `.cseq` first.

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

Under **Settings → VAG export sample rate** you can pick the default Hz value used when decoding VAG bytes to WAV for export. The HWL format doesn't store a per-sample rate (playback is derived from FX / instrument entries), so when exporting a raw sample to WAV the editor has to pick one. Choices: **11025**, **22050**, **33075**, **44100**. The selection persists across restarts via `QSettings`.

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

The validation tool (Diagnose > Validate Bank / Song) checks whether a bank contains all the SPU sample IDs that a CSEQ song needs. It reports:

- How many of the required samples are present
- A list of every missing SPU index

Note that in the actual game, multiple banks are loaded simultaneously (SFX bank + level bank + character banks). A single bank not passing validation doesn't necessarily mean the song won't play - the missing samples may be provided by another bank loaded at runtime. See the [audio loading documentation](audio-loading.md) for details on which banks the game loads together.

### Engine Limits and Warning Icons

The console imposes hard limits on audio data. Exceeding one doesn't produce an error on the console - the game may crash, play garbled audio, or silently drop sounds. The editor watches for these limits:

- **A song is too big.** Each song must fit the fixed buffer the game loads it into. A song over that size overruns the buffer and crashes or corrupts playback.
- **A level's banks don't fit in sound memory.** The samples of all the banks a race loads together must fit the console's SPU sound RAM. Samples that don't fit are dropped and go silent in game.
- **The file is too big for its slot on the disc.** The `.HWL` sits at a fixed position in the game's disc image. Growing it past the number of disc sectors it originally occupied shifts every file after it and corrupts the disc layout.
- **A note asks for more pitch than the SPU can play.** The pitch register saturates at 4.0× speed. Notes past that stop getting higher, so the affected note and every one above it collapse onto the same pitch and the part goes flat. Raising an instrument's base pitch is what brings this into range — doubling it halves the headroom. Stock songs sit about an octave clear of the ceiling.

Whenever you make an edit that would break one of these limits - replacing a sequence, importing a MIDI, adding or replacing a sample or bank, or saving a file that has grown too large - the editor warns you and lets you continue anyway (so you can keep working and fix it later, or rebuild the disc image yourself).

Items that currently exceed a limit are marked throughout the editor with a status icon: **❌** for a problem that crashes the game or makes it read garbage data, and **⚠️** for something that loads but won't sound right — for example samples that go silent. The icon appears next to the affected bank, song, or the file itself in the File Browser tree, the Category Browser, and the Music Workshop's song list; selecting the item shows a banner explaining what's wrong (hovering the icon shows the same text). Because the mark reflects the actual data, an item you chose to keep despite a warning stays flagged until you bring it back under the limit.

**Custom Mode** (Settings > Enable custom mode) turns all of this off. For mods where the stock console limits no longer apply, enabling it stops the size warnings when you edit or save and hides the status icons and banners, so you aren't nagged about limits that don't apply to your build. The Diagnose HOWL File tool still works on demand if you want to check sizes. The setting persists across restarts.

### Diagnose HOWL File

Diagnose > Diagnose HOWL File runs every engine-limit check over the whole file at once and lists what it finds, most serious first. It flags:

- Songs too big for the game's song buffer
- Level banks whose combined samples overflow SPU sound memory
- Songs that reference a sample id that doesn't exist, or one missing from the level's own banks
- **Banks whose samples are cut at the wrong offset** — the damage left behind when a shared sample was resized on behalf of another bank (see [Replacing a Shared Sample](#replacing-a-shared-sample)). Worth running on any file edited before this check existed, since the symptom shows up in a bank you never opened.
- **Notes that ask for more pitch than the console can play** — the SPU tops out at 4.0× speed, so a note past that plays flat and drags every higher note onto the same pitch
- Banks or songs whose data can't be read
- A file that has grown past the disc slot it was loaded from

Each entry explains the problem in plain terms; use **Copy to clipboard** to save the whole report. This is the same set of checks that drives the warning icons, gathered into one place so you can review a file's health at a glance.

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

The dialog warns if the selected bank exceeds the Saphi size cap. Bank/song pairing is not validated at export — use [Diagnose > Validate Bank/Song](#bank--cseq-validation) first if you want to confirm the bank contains every sample the CSEQ references.

#### Import Saphi Audio Container

**Tools > Import Saphi Audio Container...** is the inverse: pick a `.sca` file and the editor appends its bank and CSEQ as new entries on the loaded HWL (the SIZE chunk is ignored on import because the loaded HWL already has authoritative SPU sizes). A status-bar message reports the imported track's name, author, and the new bank/song indices.

Unknown chunks in the container are skipped silently for forward compatibility, so newer `.sca` files with extra metadata still import cleanly.
