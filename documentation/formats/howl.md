# HOWL (.HWL) File Format Specification

The HOWL file is the master audio container used by Crash Team Racing (PS1). It bundles all audio data for the game: SPU sample metadata, sound effect definitions, engine sound definitions, sample banks, and music sequences.

The file used in-game is `SOUNDS\KART.HWL`.

## File Layout

```
+-------------------------------+
| HOWL Header (40 bytes)        |
+-------------------------------+
| SPU Address Table             |
| (numSpuAddrs x 4 bytes)      |
+-------------------------------+
| OtherFX Table                 |
| (numOtherFX x 8 bytes)       |
+-------------------------------+
| EngineFX Table                |
| (numEngineFX x 8 bytes)      |
+-------------------------------+
| Bank Offset Table             |
| (numBanks x 2 bytes)         |
+-------------------------------+
| Song Offset Table             |
| (numSongs x 2 bytes)         |
+-------------------------------+
| [padding to sector boundary]  |
+-------------------------------+
| Bank Data Blobs               |
| (sector-aligned)              |
+-------------------------------+
| Song Data Blobs (CSEQ)        |
| (sector-aligned)              |
+-------------------------------+
```

All data blobs are aligned to **sector boundaries** (0x800 = 2048 bytes).

## HOWL Header (40 bytes)

10 little-endian 32-bit integers:

| Offset | Size | Type | Field            | Description                                         |
|--------|------|------|------------------|-----------------------------------------------------|
| 0x00   | 4    | u32  | magic            | `0x4C574F48` = ASCII "HOWL" (little-endian)         |
| 0x04   | 4    | u32  | version          | Format version. Release = `0x80`                    |
| 0x08   | 4    | u32  | reserved1        | Always 0                                            |
| 0x0C   | 4    | u32  | reserved2        | Always 0                                            |
| 0x10   | 4    | u32  | numSpuAddrs      | Number of SPU address table entries                 |
| 0x14   | 4    | u32  | numOtherFX       | Number of OtherFX (sound effect) entries            |
| 0x18   | 4    | u32  | numEngineFX      | Number of EngineFX (engine sound) entries           |
| 0x1C   | 4    | u32  | numBanks         | Number of sample banks                              |
| 0x20   | 4    | u32  | numSongs         | Number of CSEQ music sequences                     |
| 0x24   | 4    | u32  | headerDataSize   | Total byte size of all tables after this header     |

The `headerDataSize` field equals:
```
numSpuAddrs * 4 + numOtherFX * 8 + numEngineFX * 8 + numBanks * 2 + numSongs * 2
```

### Known Versions

| Value | Build                |
|-------|----------------------|
| 0x6F  | Demo (Test Drive)    |
| 0x71  | Demo (OPSM)         |
| 0x72  | Demo (Spyro)        |
| 0x78  | Beta (Aug 5)         |
| 0x7D  | Prototype            |
| 0x80  | Release (all regions)|

## SPU Address Table

Immediately follows the header. Each entry is 4 bytes:

| Offset | Size | Type | Field    | Description                                      |
|--------|------|------|----------|--------------------------------------------------|
| 0x00   | 2    | u16  | spuAddr  | SPU RAM address (in 8-byte units). Always 0 in file; populated at runtime when bank is loaded |
| 0x02   | 2    | u16  | spuSize  | Sample data size in 8-byte units. Multiply by 8 to get byte count |

The table index serves as the **global sample ID** referenced by banks, instruments, and sound effects.

### SPU Memory at Runtime

- Total SPU RAM: 512 KB (`0x7E000` bytes)
- Addresses stored as 8-byte units: `actual_byte_address = spuAddr * 8`
- `spuAddr == 0` means the sample is not currently loaded in SPU memory
- The game dynamically loads/unloads banks to manage SPU memory

## OtherFX Table (Sound Effects)

Sound effects triggered during gameplay (pickups, crashes, menu sounds, voice clips, etc.).

Each entry is 8 bytes:

| Offset | Size | Type | Field     | Description                                      |
|--------|------|------|-----------|--------------------------------------------------|
| 0x00   | 1    | u8   | flags     | Bit 2: voice clip, Bit 1: looping               |
| 0x01   | 1    | u8   | volume    | Base volume (0-255)                              |
| 0x02   | 2    | u16  | pitch     | Base pitch value                                 |
| 0x04   | 2    | u16  | spuIndex  | Index into SPU Address Table (sample ID)         |
| 0x06   | 2    | u16  | duration  | Sound duration in game frames                    |

### Playback Parameters

When a sound effect is triggered, the caller passes a flags word:

| Bits  | Field      | Description                              |
|-------|------------|------------------------------------------|
| 7:0   | volume     | Playback volume (0-255)                  |
| 15:8  | distortion | Pitch distortion (0x80 = none)           |
| 23:16 | pan        | Left/Right pan (0x80 = center)           |
| 31:24 | reverb     | Echo/reverb amount                       |

Volume calculation: `(masterVolFX * entry.volume * callVolume) >> 10`

ADSR is fixed at: Attack/Decay = `0x80FF`, Sustain/Release = `0x1FC2`

## EngineFX Table (Engine Sounds)

Vehicle engine audio. Different from OtherFX in field layout.

Each entry is 8 bytes:

| Offset | Size | Type | Field     | Description                                      |
|--------|------|------|-----------|--------------------------------------------------|
| 0x00   | 1    | u8   | flags     | Engine sound flags                               |
| 0x01   | 1    | u8   | volume    | Base volume (0-255)                              |
| 0x02   | 2    | u16  | pitch     | Base pitch value                                 |
| 0x04   | 2    | u16  | unk       | Unknown parameter                                |
| 0x06   | 2    | u16  | spuIndex  | Index into SPU Address Table (sample ID)         |

Note: The field order differs from OtherFX. In OtherFX, `spuIndex` is at offset 0x04 and `duration` at 0x06. In EngineFX, `unk` is at 0x04 and `spuIndex` at 0x06.

Engine pitch is dynamically modulated at runtime based on vehicle acceleration/RPM.

## Bank Offset Table

`numBanks` entries, each a little-endian **unsigned 16-bit** sector offset:

```
bank_byte_offset = bank_sector_offset * 0x800
```

The offset is relative to the start of the HOWL file. A value of 0 indicates an empty/unused bank slot.

## Song Offset Table

`numSongs` entries, each a little-endian **unsigned 16-bit** sector offset:

```
song_byte_offset = song_sector_offset * 0x800
```

Song data at the referenced offset contains a CSEQ sequence. See [cseq_format.md](cseq_format.md).

## Bank Data

Each bank blob starts at a sector boundary. See [bank_format.md](bank_format.md).

## KART.HWL Statistics (NTSC-U Release)

| Field           | Value |
|-----------------|-------|
| Version         | 0x80  |
| SPU Entries     | 528   |
| OtherFX Entries | 258   |
| EngineFX Entries| 20    |
| Banks           | 71    |
| Songs           | 33    |
| Header Size     | 4544  |
| File Size       | ~11.7 MB |

### Bank Names (NTSC-U)

| Index | Name             | Index | Name              |
|-------|------------------|-------|-------------------|
| 0     | sfx              | 18    | nitro_court       |
| 1     | canyon           | 19    | rampage_ruins     |
| 2     | mines            | 20    | parking_lot       |
| 3     | bluff            | 21    | skull_rock        |
| 4     | cove             | 22    | north_bowl        |
| 5     | temple           | 23    | rocky_road        |
| 6     | pyramid          | 24    | lab_basement      |
| 7     | tubes            | 25    | boss_challenge    |
| 8     | skyway           | 26    | adv_gem_valley    |
| 9     | sewer            | 27    | character_select  |
| 10    | caves            | 28    | intro             |
| 11    | castle           | 29    | cutscenes         |
| 12    | labs             | 30    | cutscenes_oxide1  |
| 13    | pass             | 31    | cutscenes_oxide2  |
| 14    | station          | 32    | credits           |
| 15    | park             | ...   | (per-character)   |
| 16    | arena            |       |                   |
| 17    | coliseum/turbo   |       |                   |

## Loading Sequence (Runtime)

1. **Initialize audio system** - Enable audio hardware, initialize SPU subsystem and reverb modes
2. **Load HOWL header** - Read the first sector(s) from CD into RAM, then parse the header to set up pointer arrays for the SPU table, FX tables, and offset tables
3. **Per-level loading** (5 asynchronous stages):
   - Stage 0: Load level sound effects bank
   - Stage 1: Load default 8-driver bank (shared across all levels)
   - Stage 2: Load per-character voice/sound banks
   - Stage 3: Load level music bank
   - Stage 4: Load and parse CSEQ sequence data
4. **Bank loading** - 4-stage async pipeline per bank: read bank header from disc, assign SPU addresses for each sample, DMA transfer sample data to SPU RAM, verify transfer completion
5. **Song loading** - Read CSEQ data from disc, parse the CSEQ header and instrument tables, set up playback structures

## Channel Types

The game uses 3 channel types for audio playback:

| Type | Value | Description                                    |
|------|-------|------------------------------------------------|
| Engine | 0   | Engine sounds (continuous, pitch-modulated)    |
| Other  | 1   | Sound effects (timed duration)                 |
| Music  | 2   | CSEQ music notes (sequenced)                  |

## Frequency Encoding

Internal frequency values use 4096 as a base corresponding to 44100 Hz:

```
frequency_hz = (internal_value / 4096) * 44100
internal_value = (frequency_hz * 4096) / 44100
```

| Internal | Hz     |
|----------|--------|
| 4096     | 44100  |
| 2048     | 22050  |
| 1024     | 11025  |
