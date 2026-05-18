# coding: utf-8

from dataclasses import dataclass, field


@dataclass
class MidiTrackInfo:
    """Info about a single MIDI track."""
    index: int = 0
    name: str = ""
    note_count: int = 0
    channels: list[int] = field(default_factory=list)
    drum_pitches: list[int] = field(default_factory=list)


@dataclass
class MidiInfo:
    """Summary info about a MIDI file."""
    midi_type: int = 0
    ticks_per_beat: int = 480
    num_tracks: int = 0
    tracks: list[MidiTrackInfo] = field(default_factory=list)


@dataclass
class DrumPitchMapping:
    """Per-percussion mapping for a single MIDI drum pitch.

    CSEQ drum tracks treat NOTE_ON.pitch as an index into Percussions[], so
    each unique MIDI drum pitch needs its own CseqPercussion entry pointing
    at a real SPU sample.
    """
    midi_pitch: int = 0
    sample_id: int = 0
    frequency: int = 0x1000
    volume: int = 255


@dataclass
class InstrumentMapping:
    """Maps a MIDI track to one CTR SPU instrument (melodic) or a list of
    percussion slots, one per detected drum pitch (drum tracks)."""
    sample_id: int = 0
    frequency: int = 0x1000
    volume: int = 255
    adsr: int = 0x1FC180FF
    is_drum: bool = False
    drum_pitches: list[DrumPitchMapping] = field(default_factory=list)


@dataclass
class MidiConvertSettings:
    """Configuration for MIDI to CSEQ conversion."""
    mappings: list[InstrumentMapping] = field(default_factory=list)
    default_bpm: int = 120
