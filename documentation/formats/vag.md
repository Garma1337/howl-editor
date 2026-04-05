# VAG (PlayStation ADPCM) Format Specification

VAG is the standard audio sample format for the PlayStation 1. It stores audio compressed using ADPCM (Adaptive Differential Pulse-Code Modulation) at a 4:1 compression ratio.

## Standalone VAG File

When stored as a standalone `.vag` file, a 48-byte header precedes the sample data.

### VAG Header (48 bytes)

All header fields are **big-endian** (unlike most PS1 data which is little-endian).

| Offset | Size | Type   | Field       | Description                          |
|--------|------|--------|-------------|--------------------------------------|
| 0x00   | 4    | bytes  | magic       | `VAGp` (0x56414770)                 |
| 0x04   | 4    | u32 BE | version     | Always 3                             |
| 0x08   | 4    | u32 BE | reserved    | Always 0                             |
| 0x0C   | 4    | u32 BE | dataSize    | Size of sample data in bytes         |
| 0x10   | 4    | u32 BE | sampleRate  | Sample rate in Hz (e.g., 11025)      |
| 0x14   | 12   | bytes  | reserved    | Always 0                             |
| 0x20   | 16   | ASCII  | name        | Sample name, null-padded             |

Sample data starts at offset 0x30 (48 bytes).

## In-Bank VAG Data

When stored inside a HOWL bank, VAG data has **no header**. It is raw ADPCM frame data. The sample rate and size are determined from the CSEQ instrument definition and SPU Address Table respectively.

## ADPCM Frame Structure

Each VAG frame is **16 bytes** and decodes to **28 audio samples** (56 bytes of 16-bit PCM).

| Offset | Size | Type | Field    | Description                              |
|--------|------|------|----------|------------------------------------------|
| 0x00   | 1    | u8   | control  | Upper 4 bits: predict_nr, Lower 4 bits: shift_factor |
| 0x01   | 1    | u8   | flags    | Frame flags (see below)                  |
| 0x02   | 14   | bytes| data     | 28 ADPCM nibbles (2 samples per byte, low nibble first) |

### Frame Flags

| Value | Meaning                                   |
|-------|-------------------------------------------|
| 0     | Normal frame                              |
| 2     | Loop end point                            |
| 3     | Loop end + loop marker                    |
| 6     | Loop start marker                         |
| 7     | End of sample (last frame)                |

### ADPCM Prediction Coefficients

The `predict_nr` selects a pair of filter coefficients:

| predict_nr | f0       | f1       |
|------------|----------|----------|
| 0          | 0.0      | 0.0      |
| 1          | 60/64    | 0.0      |
| 2          | 115/64   | -52/64   |
| 3          | 98/64    | -55/64   |
| 4          | 122/64   | -60/64   |

### Decoding Algorithm

For each nibble in the data:

```
sample = sign_extend_4bit(nibble) << (12 - shift_factor)
sample += (prev1 * f0 + prev2 * f1) / 64
output = clamp(sample, -32768, 32767)
prev2 = prev1
prev1 = output
```

## SPU Address Table Relationship

In the HOWL file, the SPU Address Table maps global sample IDs to sizes:

```
actual_byte_size = spu_addrs[sampleID].spuSize * 8
num_frames = actual_byte_size / 16
num_pcm_samples = num_frames * 28
```

## Common Sample Rates

| Rate   | Usage                                    |
|--------|------------------------------------------|
| 11025  | Most CTR sound effects and music samples |
| 22050  | Higher quality effects                   |
| 44100  | Rare, highest quality                    |
