# coding: utf-8

"""MIDI-side constants shared by the importer and exporter."""

# General MIDI controller numbers used by CTR's music: master volume
# maps to CSEQ's VELOCITY event, pan maps to CSEQ's PAN event.
CC_VOLUME = 7
CC_PAN = 10

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
