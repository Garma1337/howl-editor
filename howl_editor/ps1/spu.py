# coding: utf-8

"""PS1 SPU register-layout facts."""


# The SPU's ADSR envelope counter is a 15-bit value (0..0x7FFF).
MAX_ENVELOPE = 0x7FFF

# Attack / release shift-rate registers are each 5 bits (0..31).
MAX_ATTACK_SHIFT = 31
MAX_RELEASE_SHIFT = 31

# Decay shift-rate register is 4 bits (0..15).
MAX_DECAY_SHIFT = 15

# Sustain shift-rate register is 5 bits (0..31), same width as attack/release.
MAX_SUSTAIN_SHIFT = 31

# Sustain-level field is 4 bits; the SPU maps raw N to (N+1)/16 of full scale.
SUSTAIN_LEVEL_STEPS = 16

# The SPU has 512 KB of dedicated sample RAM. A small reserved area near the
# top is used by the SPU itself, but everything an audio engine uploads needs
# to fit under this ceiling.
RAM_BYTES = 512 * 1024

# SPU mixing / output sample rate.
SAMPLE_RATE = 44100.0

# Unit of the SPU's pitch register: pitch == FREQUENCY_UNIT means 1.0× sample
# playback ratio. Halving plays an octave down, doubling plays an octave up.
FREQUENCY_UNIT = 4096.0
