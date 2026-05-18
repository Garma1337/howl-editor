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
