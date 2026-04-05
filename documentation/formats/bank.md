# Bank Format Specification

A bank is a collection of audio samples stored as a sector-aligned blob within the HOWL file. Banks are loaded at runtime to populate SPU RAM with sample data for sound effects and music.

## Bank Layout

```mermaid
block-beta
  columns 1
  A["Sample Count (2 bytes)"]
  B["Sample ID Array\n(numSamples x 2 bytes)"]
  C["Padding to sector boundary"]
  D["Sample Data\n(concatenated headerless VAG frames)"]

  style C fill:#555,stroke:#888
```

## Bank Header

```mermaid
packet-beta
  0-15: "numSamples (s16)"
  16-31: "sampleID[0] (s16)"
  32-47: "sampleID[1] (s16)"
  48-63: "... (s16)"
```

- **numSamples**: Number of samples in this bank (max ~1023)
- **sampleID[i]**: Global SPU Address Table index for sample `i`

## Padding

After the header + sample ID array, the data is padded to the next **sector boundary** (0x800 = 2048 bytes). The sample data begins at this boundary.

```
header_bytes = 2 + numSamples * 2
data_offset = ceil(header_bytes / 2048) * 2048
```

## Sample Data

Starting at the sector boundary, samples are stored **sequentially without gaps**. Each sample's size is determined by the SPU Address Table:

```
sample_byte_size = spu_addrs[sampleID].spuSize * 8
```

The sample data is raw VAG ADPCM frames (headerless). See [vag.md](vag.md) for the frame encoding.

## How Banks Reference Samples

```mermaid
flowchart LR
  subgraph Bank
    H["Header\nnumSamples=3"]
    ID0["sampleID[0] = 10"]
    ID1["sampleID[1] = 25"]
    ID2["sampleID[2] = 42"]
  end

  subgraph SPU["SPU Address Table"]
    E10["[10] spuSize=120"]
    E25["[25] spuSize=200"]
    E42["[42] spuSize=80"]
  end

  subgraph Data["Bank Sample Data"]
    D0["VAG data\n(120 * 8 bytes)"]
    D1["VAG data\n(200 * 8 bytes)"]
    D2["VAG data\n(80 * 8 bytes)"]
  end

  ID0 --> E10
  ID1 --> E25
  ID2 --> E42
  E10 -. "size" .-> D0
  E25 -. "size" .-> D1
  E42 -. "size" .-> D2
```

## Runtime Loading

The game loads banks through a 4-stage asynchronous pipeline:

```mermaid
flowchart TD
  S0["Stage 0: Read header\n(first sector from CD)"] --> S1
  S1["Stage 1: Assign SPU addresses\n(skip samples already loaded)"] --> S2
  S2["Stage 2: DMA transfer\n(RAM → SPU memory)"] --> S3
  S3["Stage 3: Verify transfer\n(mark bank loaded, free RAM)"]
```

### Stage 0: Load Header
- Read the first sector of the bank from CD into RAM
- This contains the sample count and ID array

### Stage 1: Calculate Sizes and Assign SPU Addresses
- Sum all `spuSize` values for samples in the bank (multiplied by 8 for byte count)
- For each sample where `spuAddr == 0` (not yet loaded), assign a new SPU address from the allocation pointer
- Track the address range (min/max) for this bank

### Stage 2: DMA Transfer
- Transfer sample data from RAM to SPU memory via DMA

### Stage 3: Verify Transfer
- Wait for SPU transfer completion
- Mark bank as loaded
- Free temporary RAM allocation

## Bank Destruction

When SPU memory needs to be reclaimed, the game scans the SPU Address Table and resets any entry with `spuAddr` within the target range back to 0. This allows the SPU memory region to be reused by future bank loads.

## Sample Deduplication

Multiple banks can reference the same sample ID. When loading a bank, if a sample's `spuAddr` is already non-zero (loaded by a previous bank), the SPU address is preserved and the data is not re-transferred. This saves SPU memory when banks share samples (e.g., the common SFX bank shares samples with level-specific banks).

## Example

For a bank with 3 samples referencing SPU IDs [10, 25, 42]:

```
Offset 0x000: 03 00           numSamples = 3
Offset 0x002: 0A 00           sampleID[0] = 10
Offset 0x004: 19 00           sampleID[1] = 25
Offset 0x006: 2A 00           sampleID[2] = 42
Offset 0x008-0x7FF: 00...     padding to sector boundary
Offset 0x800: [VAG data]      sample 10 data (size = spu_addrs[10].spuSize * 8)
              [VAG data]      sample 25 data (size = spu_addrs[25].spuSize * 8)
              [VAG data]      sample 42 data (size = spu_addrs[42].spuSize * 8)
```
