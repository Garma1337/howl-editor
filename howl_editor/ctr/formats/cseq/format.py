# coding: utf-8

"""CSEQ binary layout — numbers reader and writer must agree on.

File structure overview:

    +-------------------------------+
    | header (size + 4 counts)      |  CseqInfo.HEADER_SIZE
    +-------------------------------+
    | instrument table              |  N × CseqInstrument.SIZE
    +-------------------------------+
    | percussion table              |  M × CseqPercussion.SIZE
    +-------------------------------+
    | song offset table             |  K × OFFSET_SIZE  (padded to ALIGNMENT)
    +-------------------------------+
    | song 0                        |
    |   song header                 |  SONG_HEADER_SIZE
    |   track offset table          |  T × OFFSET_SIZE  (padded to ALIGNMENT)
    |   track 0 … track T-1         |  each: TRACK_HEADER_SIZE + events
    | song 1, song 2 …              |
    +-------------------------------+
"""

# Size of one 16-bit big-step offset inside the song / track offset tables.
OFFSET_SIZE = 2

# Per-song header: u8 unk0 + u8 num_tracks + i16 bpm + i16 tpqn.
SONG_HEADER_SIZE = 6

# Per-track header: u8 flags + u8 unk.
TRACK_HEADER_SIZE = 2

# The PS1 MIPS loader expects 4-byte aligned read positions, so the
# offset tables are padded out to this many bytes.
ALIGNMENT = 4

# CSEQ VELOCITY (master volume) and PAN events store one byte each.
CC_MAX = 255

# CSEQ PITCH_BEND stores a single byte; the center (no bend) is 0x80 / 2 ≈ 128
# but the wire format simply allows 0..255 so importers clamp here.
MAX_PITCH_BEND = 255

# CseqInstrument.volume and CseqPercussion.volume are u8 in the on-wire
# struct, so the maximum legal value is 0xFF.
MAX_VOLUME = 0xFF

# CseqInstrument.frequency and CseqPercussion.frequency are u16 in the on-wire
# struct (the SPU pitch register the runtime writes), so the maximum legal
# value is 0xFFFF. spu.FREQUENCY_UNIT (4096) maps to 1.0× playback rate.
MAX_PITCH_REGISTER = 0xFFFF

# Fallback base pitch offered for a sample nothing in the file references yet,
# so there is no stored pitch to copy. Nothing can derive the right value here:
# the correct base pitch depends on the musical pitch of the recording, which a
# VAG does not carry. 0x400 is only the value this editor has always defaulted
# to (it plays a sample back at 11025 Hz) — the user is expected to set it by
# listening, not to trust it.
DEFAULT_BASE_PITCH = 0x400

# CseqInstrument.adsr is u32 in the on-wire struct — it's the raw SPU
# ADSR register pair. Bits 0-15 are ADSR1 (attack/decay/sustain level),
# bits 16-31 are ADSR2 (sustain rate/release). Each half is a u16.
MAX_ADSR_REGISTER = 0xFFFFFFFF
MAX_ADSR_HALF = 0xFFFF
