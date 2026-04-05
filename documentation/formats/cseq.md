# CSEQ Sequence Format Specification

CSEQ is CTR's music sequence format, similar to MIDI. Each CSEQ blob (stored as a "song" in the HOWL file) contains instrument definitions, percussion definitions, and one or more playable sequences with tracks of timed note/control events.

## File Layout

```
+------------------------------------+
| CSEQ Header (8 bytes)              |
+------------------------------------+
| Instrument Table                   |
| (numInstruments x 12 bytes)        |
+------------------------------------+
| Percussion Table                   |
| (numPercussions x 8 bytes)         |
+------------------------------------+
| Song Offset Table                  |
| (numSongs x 2 bytes)              |
+------------------------------------+
| [padding to 4-byte alignment]     |
+------------------------------------+
| Song Data (variable length)        |
|   Song 0                           |
|   Song 1                           |
|   ...                              |
+------------------------------------+
```

## CSEQ Header (8 bytes)

| Offset | Size | Type | Field           | Description                                |
|--------|------|------|-----------------|--------------------------------------------|
| 0x00   | 4    | u32  | fileSize        | Total CSEQ size including this field       |
| 0x04   | 1    | u8   | numInstruments  | Number of instrument (long sample) entries |
| 0x05   | 1    | u8   | numPercussions  | Number of percussion (short sample) entries|
| 0x06   | 1    | u8   | numSongs        | Number of sequences in this CSEQ           |
| 0x07   | 1    | u8   | padding         | Filler byte (always 0)                     |

Note: `numSongs` and `padding` occupy the same 2 bytes that could be read as a single `u16`. Both interpretations produce the same result since `padding` is always 0.

## Instrument Table (Long Samples)

Each instrument entry is 12 bytes. These define melodic instruments used by tracks.

| Offset | Size | Type | Field       | Description                                          |
|--------|------|------|-------------|------------------------------------------------------|
| 0x00   | 1    | u8   | flags       | Always 1 in original data. Bit meanings: 1=music sample, 2=looped, 4=voice clip |
| 0x01   | 1    | u8   | volume      | Sample volume (0-255)                                |
| 0x02   | 2    | s16  | timeToPlay  | Delay before NoteOff. 0 for music, ~300 for ~1 sec  |
| 0x04   | 2    | u16  | frequency   | Base pitch. 4096 = 44100 Hz (see frequency encoding) |
| 0x06   | 2    | u16  | sampleID    | Index into HOWL SPU Address Table                    |
| 0x08   | 2    | u16  | ad          | PSX SPU ADSR Attack/Decay register value             |
| 0x0A   | 2    | u16  | sr          | PSX SPU ADSR Sustain/Release register value          |

The `ad` and `sr` fields are raw PSX SPU ADSR register values passed directly to the hardware. Common values: `ad = 0x80FF`, `sr = 0x1FC2`.

These can be stored as a single 32-bit value: `adsr = (sr << 16) | ad`.

### Instrument Volume Calculation (Runtime)

```
final_volume = (masterVolMusic * songVol * seqVol * instrument.volume) >> 10
```

## Percussion Table (Short Samples)

Each percussion entry is 8 bytes. These define drum/percussion instruments.

| Offset | Size | Type | Field       | Description                                          |
|--------|------|------|-------------|------------------------------------------------------|
| 0x00   | 1    | u8   | flags       | Always 1 in original data                            |
| 0x01   | 1    | u8   | volume      | Sample volume (0-255)                                |
| 0x02   | 2    | u16  | frequency   | Base pitch. 4096 = 44100 Hz                          |
| 0x04   | 2    | u16  | sampleID    | Index into HOWL SPU Address Table                    |
| 0x06   | 2    | s16  | timeToPlay  | Delay parameter (usually 0)                          |

Note: Percussion uses **fixed ADSR** values: `ad = 0x80FF`, `sr = 0x1FC2`. These are not stored in the file.

Note: The field order differs from instruments. In instruments, `timeToPlay` is at offset 0x02 and `sampleID` at 0x06. In percussion, `sampleID` is at offset 0x04 and `timeToPlay` at 0x06.

## Song Offset Table

`numSongs` entries, each a little-endian **signed 16-bit** offset. These are byte offsets relative to the start of the song data section (after alignment padding).

## Song Data

### Song Header (6 bytes)

Each song begins at its offset within the song data section:

| Offset | Size | Type | Field    | Description                              |
|--------|------|------|----------|------------------------------------------|
| 0x00   | 1    | u8   | unk      | Unknown byte (preserved during playback) |
| 0x01   | 1    | u8   | numSeqs  | Number of tracks/sequences               |
| 0x02   | 2    | s16  | bpm      | Beats per minute                         |
| 0x04   | 2    | s16  | tpqn     | Ticks per quarter note                   |

### Track Offset Table

Immediately after the song header: `numSeqs` entries, each a little-endian **unsigned 16-bit** byte offset relative to the start of the track data area.

After the track offset table, padding is applied to align to a 4-byte boundary.

### Track Structure

Each track starts with a 2-byte header:

| Offset | Size | Type | Field | Description                                         |
|--------|------|------|-------|-----------------------------------------------------|
| 0x00   | 1    | u8   | flags | Bit 0: 1 = percussion/drum track, 0 = melodic track|
| 0x01   | 1    | u8   | unk   | Unknown parameter (copied to sequence state)        |

Followed by a variable-length sequence of events.

## Event Format

Each event consists of:

1. **Delta time** - Variable-length quantity (VLQ), see below
2. **Opcode** - Single byte (0x00-0x0A)
3. **Parameters** - 0-2 bytes depending on opcode

### Opcodes

| Value | Name         | Params | Description                              |
|-------|--------------|--------|------------------------------------------|
| 0x00  | Terminator   | 0      | End of event data (terminal)             |
| 0x01  | NoteOff      | 1      | Stop note. Param: pitch/drum index       |
| 0x02  | EndTrack2    | 1      | Alternate end track (terminal)           |
| 0x03  | EndTrack     | 0      | End of track (terminal)                  |
| 0x04  | Unknown4     | 1      | Unknown control event                    |
| 0x05  | NoteOn       | 2      | Start note. Params: pitch, velocity      |
| 0x06  | Velocity     | 1      | Set track volume. Param: velocity        |
| 0x07  | Pan          | 1      | Set stereo pan. Param: pan (0x80=center) |
| 0x08  | Unknown8     | 1      | Unknown control (reverb-related?)        |
| 0x09  | ChangePatch  | 1      | Select instrument. Param: instrument ID  |
| 0x0A  | PitchBend    | 1      | Bend pitch. Param: bend amount           |

Terminal events (Terminator, EndTrack, EndTrack2) signal the end of event data for a track.

### NoteOn (0x05)

Parameters:
- Byte 1: Pitch index (for melodic) or drum index (for percussion)
- Byte 2: Velocity (volume, 0-255)

For melodic tracks, the pitch is used to look up a frequency from a note table. For drum tracks, the pitch is a direct index into the percussion table.

### ChangePatch (0x09)

Sets the current instrument for subsequent NoteOn events. The parameter is an index into either the instrument table (melodic tracks) or percussion table (drum tracks).

## Variable-Length Quantity (VLQ)

Delta times use MIDI-style variable-length encoding:

- Each byte contributes 7 data bits (bits 6:0)
- Bit 7 (MSB) is a continuation flag: 1 = more bytes follow, 0 = final byte
- Bytes are in big-endian bit order

### Examples

| Bytes          | Value  |
|----------------|--------|
| `0x00`         | 0      |
| `0x7F`         | 127    |
| `0x81 0x00`    | 128    |
| `0x81 0x48`    | 200    |
| `0xFF 0x7F`    | 16383  |

### Decoding Algorithm

```
result = 0
loop:
    byte = read_next_byte()
    result = (result << 7) | (byte & 0x7F)
    if (byte & 0x80) == 0:
        return result
```

## Pitch and Frequency

Instrument frequencies use the encoding: `4096 = 44100 Hz`

```
frequency_hz = (internal_value / 4096) * 44100
internal_value = (frequency_hz * 4096) / 44100
```

At runtime, note pitch modifies the base frequency using a lookup table indexed by note number and octave, with optional distortion modifiers.
