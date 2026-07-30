# coding: utf-8

"""MIDI-side constants shared by the importer and exporter."""

# General MIDI controller numbers used by CTR's music: master volume
# maps to CSEQ's VELOCITY event, pan maps to CSEQ's PAN event.
CC_VOLUME = 7
CC_PAN = 10

# GM "Effects 1 Depth" is the conventional reverb-send controller, so CSEQ's
# REVERB (0x08) round-trips through it. Nothing in GM matches CTR's per-voice
# SPU reverb exactly — this is a carrier so the event survives a DAW round
# trip, not a claim that a DAW will reproduce the console's reverb.
CC_REVERB = 91

# MIDI controller values are 7-bit.
CC_MAX = 127

# MIDI pitch-wheel range. Signed 14-bit (−8192…8191) — mido reports it
# centered at 0; CTR's writers use the unsigned form (0…16383, center 8192).
PITCH_BEND_RANGE = 16384
PITCH_BEND_CENTER = 8192

# General-MIDI drum channel is 1-based 10 = 0-based index 9 in `mido`.
DRUM_CHANNEL_INDEX = 9

# Highest MIDI channel index `mido` ever emits (0..15).
MAX_CHANNEL_INDEX = 15
