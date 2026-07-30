# coding: utf-8

from dataclasses import dataclass, field
from enum import IntEnum
from struct import Struct

from howl_editor.ps1 import spu


class CseqEventType(IntEnum):
    TERMINATOR = 0x00
    NOTE_OFF = 0x01
    END_TRACK_2 = 0x02
    END_TRACK = 0x03
    UNKNOWN_4 = 0x04
    NOTE_ON = 0x05
    VELOCITY = 0x06
    PAN = 0x07
    REVERB = 0x08
    CHANGE_PATCH = 0x09
    PITCH_BEND = 0x0A


# The four opcodes the runtime re-applies to voices that are ALREADY sounding
# (cseq_opcode06/07/08/0a each walk the sequence's live channels and re-flag
# HOWL_CHANNEL_UPDATE_DYNAMIC_ATTRS). Everything else only affects notes
# started after it. This is CTR's whole runtime-modulation surface.
CSEQ_MODULATION_EVENTS = frozenset({
    CseqEventType.VELOCITY,
    CseqEventType.PAN,
    CseqEventType.REVERB,
    CseqEventType.PITCH_BEND,
})

# Everything the event editor is willing to touch. Beyond the modulation set
# this adds the two note opcodes and CHANGE_PATCH, because those are what bind
# a track to a descriptor: a drum NOTE_ON's byte IS the index into
# Percussions[], and CHANGE_PATCH picks the entry in Instruments[]. Without
# them a newly added descriptor is unreachable from any sequence.
CSEQ_EDITABLE_EVENTS = CSEQ_MODULATION_EVENTS | frozenset({
    CseqEventType.NOTE_ON,
    CseqEventType.NOTE_OFF,
    CseqEventType.CHANGE_PATCH,
})


CSEQ_EVENT_PARAMS: dict[CseqEventType, int] = {
    CseqEventType.TERMINATOR: 0,
    CseqEventType.NOTE_OFF: 1,
    CseqEventType.END_TRACK_2: 1,
    CseqEventType.END_TRACK: 0,
    CseqEventType.UNKNOWN_4: 1,
    CseqEventType.NOTE_ON: 2,
    CseqEventType.VELOCITY: 1,
    CseqEventType.PAN: 1,
    CseqEventType.REVERB: 1,
    CseqEventType.CHANGE_PATCH: 1,
    CseqEventType.PITCH_BEND: 1,
}

CSEQ_TERMINAL_EVENTS = frozenset({
    CseqEventType.END_TRACK,
    CseqEventType.END_TRACK_2,
    CseqEventType.TERMINATOR,
})


@dataclass
class CseqInstrument:
    """Long instrument definition (12 bytes in file)."""
    STRUCT = Struct("<BBhHHI")
    SIZE = STRUCT.size

    flags: int = 1
    volume: int = 255
    time_to_play: int = 0
    frequency: int = 0x1000
    sample_id: int = 0
    adsr: int = 0x1FC180FF

    @property
    def freq_hz(self) -> int:
        return int(self.frequency / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)

    @freq_hz.setter
    def freq_hz(self, hz: int):
        self.frequency = int(hz * spu.FREQUENCY_UNIT / spu.SAMPLE_RATE)


@dataclass
class CseqPercussion:
    """Short instrument/percussion definition (8 bytes in file)."""
    STRUCT = Struct("<BBHHh")
    SIZE = STRUCT.size

    flags: int = 1
    volume: int = 255
    frequency: int = 0x1000
    sample_id: int = 0
    time_to_play: int = 0

    @property
    def freq_hz(self) -> int:
        return int(self.frequency / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)

    @freq_hz.setter
    def freq_hz(self, hz: int):
        self.frequency = int(hz * spu.FREQUENCY_UNIT / spu.SAMPLE_RATE)


@dataclass
class CseqEvent:
    delta: int = 0
    event_type: CseqEventType = CseqEventType.END_TRACK
    pitch: int = 0
    velocity: int = 0


@dataclass
class CseqTrack:
    flags: int = 0   # Bit 0: 1=percussion/drum, 0=melodic
    unk: int = 0     # Unknown parameter (preserved from original data)
    events: list[CseqEvent] = field(default_factory=list)
    instrument: int = 0

    @property
    def is_drum(self) -> bool:
        return (self.flags & 1) != 0


@dataclass
class CseqSong:
    unk0: int = 0
    bpm: int = 120
    tpqn: int = 480
    tracks: list[CseqTrack] = field(default_factory=list)


@dataclass
class CseqFile:
    instruments: list[CseqInstrument] = field(default_factory=list)
    percussions: list[CseqPercussion] = field(default_factory=list)
    songs: list[CseqSong] = field(default_factory=list)


@dataclass
class CseqInfo:
    """Lightweight summary of a CSEQ, parsed from the header only."""
    HEADER_STRUCT = Struct("<IBBh")
    HEADER_SIZE = HEADER_STRUCT.size

    file_size: int = 0
    num_instruments: int = 0
    num_percussions: int = 0
    num_songs: int = 0
