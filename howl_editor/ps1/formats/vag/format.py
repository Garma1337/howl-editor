# coding: utf-8

"""Sony VAG (ADPCM) binary layout.

Frame layout:

    byte 0: prediction filter index (high nibble) + shift (low nibble)
    byte 1: flags (end-of-stream marker etc.)
    bytes 2..15: 28 packed 4-bit ADPCM nibbles
                 → decodes to 28 int16 PCM samples
"""

# Bytes per encoded VAG frame.
FRAME_SIZE = 16

# Header bytes at the top of each frame (predict/shift + flags).
FRAME_HEADER_SIZE = 2

# Decoded PCM samples produced by one VAG frame.
PCM_SAMPLES_PER_FRAME = 28

# ADPCM nibble sign-correction: nibble values 8..15 are negative — subtract
# this offset after un-shifting to recover signed int.
NIBBLE_SIGN_THRESHOLD = 8
NIBBLE_SIGN_OFFSET = 16

# Q12 fixed point used for the predictor → audible-sample conversion.
ADPCM_FIXED_POINT_SHIFT = 12

# Filter coefficients are stored /64 in the format; rounding and shift used
# when blending the prediction with the new sample.
FILTER_ROUNDING = 32
FILTER_SHIFT = 6

# PSX VAG ADPCM prediction filter coefficients (fixed-point, divided by 64).
# The wire format's per-frame predict_nr byte indexes into this table; the
# decoder must use exactly these values to reproduce the original samples.
FILTER_COEFFICIENTS = [
    (0, 0),
    (60, 0),
    (115, -52),
    (98, -55),
    (122, -60),
]

# Per-frame flag-byte values. Bit-flag bits combine; FLAG_END_OF_DATA is a
# whole-byte sentinel that some encoders emit instead of LOOP_END|LOOP_REPEAT.
FLAG_LOOP_END = 1
FLAG_LOOP_REPEAT = 2
FLAG_LOOP_START = 4
FLAG_END_OF_DATA = 7

# Sample name field inside the VAG container header: 16 ASCII bytes starting
# at offset 0x20, NUL-terminated / NUL-padded.
NAME_OFFSET = 0x20
NAME_LENGTH = 16

# Version byte of the VAG container header. CTR ships v3 files; the writer emits the same.
VERSION = 3
