# coding: utf-8

from pathlib import Path

import pytest

from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from howl_editor.ctr.formats.cseq.models import CseqEventType
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.drum_pitch_remapper import DrumPitchRemapper
from howl_editor.midi.models import (
    MidiConvertSettings, InstrumentMapping, DrumPitchMapping,
)

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

pytestmark = pytest.mark.skipif(not HAS_MIDO, reason="mido not installed")


def _converter():
    vlq = VlqCodec()
    return MidiConverter(CseqWriter(vlq), DrumPitchRemapper())


def _reader():
    return CseqReader(VlqCodec(), StockNameResolver())


def _create_midi(tmp_path: Path, bpm: int = 120, notes: list[tuple[int, int, int]] | None = None) -> Path:
    """Create a simple MIDI file with optional notes as (pitch, velocity, duration_ticks)."""
    mid = mido.MidiFile(type=1, ticks_per_beat=480)

    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    tempo_track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(tempo_track)

    if notes:
        note_track = mido.MidiTrack()

        for pitch, vel, dur in notes:
            note_track.append(mido.Message("note_on", note=pitch, velocity=vel, time=0))
            note_track.append(mido.Message("note_off", note=pitch, velocity=0, time=dur))

        note_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(note_track)

    path = tmp_path / "test.mid"
    mid.save(str(path))
    return path


class TestGetMidiInfo:

    def test_reads_basic_info(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, bpm=140, notes=[(60, 100, 480)])
        info = conv.get_midi_info(path)

        assert info.midi_type == 1
        assert info.ticks_per_beat == 480
        assert info.num_tracks == 2

    def test_track_info(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, notes=[(60, 100, 480), (64, 80, 240)])
        info = conv.get_midi_info(path)
        note_track = info.tracks[1]

        assert note_track.note_count == 2


class TestConvert:

    def test_produces_valid_cseq(self, tmp_path):
        conv = _converter()
        reader = _reader()
        path = _create_midi(tmp_path, notes=[(60, 100, 480)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0, frequency=0x1000)],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.songs) == 1
        assert len(cseq.songs[0].tracks) >= 1

    def test_drum_track(self, tmp_path):
        conv = _converter()
        reader = _reader()
        path = _create_midi(tmp_path, notes=[(36, 100, 120)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(is_drum=True, sample_id=0)],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.percussions) == 1

    def test_extracts_tempo(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, bpm=150, notes=[(60, 100, 480)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)

        assert cseq.songs[0].bpm == 150

    def test_no_notes_produces_empty_tracks(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path)
        settings = MidiConvertSettings()
        cseq = conv.convert_to_model(path, settings)

        assert len(cseq.songs[0].tracks) == 0

    def test_cc_volume_scaled_from_7bit_to_8bit(self, tmp_path):
        """CTR expects 0-255 for VELOCITY events; MIDI CC#7 is 0-127. The full
        MIDI range must hit the full CSEQ range or songs come out half-volume."""
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        cc_track = mido.MidiTrack()
        cc_track.append(mido.Message("control_change", control=7, value=127, time=0))
        cc_track.append(mido.Message("control_change", control=7, value=0, time=10))
        cc_track.append(mido.Message("control_change", control=7, value=64, time=10))
        cc_track.append(mido.Message("note_on", note=60, velocity=100, time=10))
        cc_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        cc_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(cc_track)
        path = tmp_path / "vol.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )
        cseq = conv.convert_to_model(path, settings)
        velocity_events = [
            e for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.VELOCITY
        ]

        assert [e.pitch for e in velocity_events] == [255, 0, 128]

    def test_cc_pan_scaled_from_7bit_to_8bit(self, tmp_path):
        """CC#10 (pan) likewise expands from 0-127 to 0-255."""
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        cc_track = mido.MidiTrack()
        cc_track.append(mido.Message("control_change", control=10, value=127, time=0))
        cc_track.append(mido.Message("note_on", note=60, velocity=100, time=10))
        cc_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        cc_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(cc_track)
        path = tmp_path / "pan.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )
        cseq = conv.convert_to_model(path, settings)
        pan_events = [
            e for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.PAN
        ]

        assert pan_events and pan_events[0].pitch == 255

    def test_drum_track_creates_one_percussion_per_unique_pitch(self, tmp_path):
        """MIDI drum tracks usually have many GM pitches (36 kick, 38 snare,
        42 hi-hat). Each needs its own CseqPercussion slot — CTR-tools does
        the same in HowlControl.cs ImportMIDI."""
        conv = _converter()
        reader = _reader()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (36, 38, 42, 36, 38):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "drums.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[
                InstrumentMapping(),
                InstrumentMapping(is_drum=True, drum_pitches=[
                    DrumPitchMapping(midi_pitch=36, sample_id=10),
                    DrumPitchMapping(midi_pitch=38, sample_id=11),
                    DrumPitchMapping(midi_pitch=42, sample_id=12),
                ]),
            ],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.percussions) == 3
        assert [p.sample_id for p in cseq.percussions] == [10, 11, 12]

    def test_drum_track_remaps_note_pitches_to_percussion_indices(self, tmp_path):
        """The on-disk NOTE_ON pitch must be 0, 1, 2... (Percussions[] index),
        not the original MIDI note number — otherwise the game reads past the
        percussion table."""
        conv = _converter()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (38, 36, 42):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "remap.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[
                InstrumentMapping(),
                InstrumentMapping(is_drum=True, drum_pitches=[
                    DrumPitchMapping(midi_pitch=36, sample_id=0),
                    DrumPitchMapping(midi_pitch=38, sample_id=1),
                    DrumPitchMapping(midi_pitch=42, sample_id=2),
                ]),
            ],
        )

        cseq = conv.convert_to_model(path, settings)
        drum_cseq_track = cseq.songs[0].tracks[0]
        note_on_pitches = [
            e.pitch for e in drum_cseq_track.events
            if e.event_type == CseqEventType.NOTE_ON
        ]

        # MIDI order was 38, 36, 42 — the user's table order was 36, 38, 42 →
        # remap indices: 1, 0, 2.
        assert note_on_pitches == [1, 0, 2]

    def test_melodic_track_pitches_pass_through_unchanged(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, notes=[(60, 100, 240), (64, 90, 240)])
        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)
        notes = [
            e.pitch for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.NOTE_ON
        ]

        assert notes == [60, 64]

    def test_get_midi_info_reports_drum_pitches(self, tmp_path):
        conv = _converter()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (42, 36, 38, 36):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "info.mid"
        mid.save(str(path))

        info = conv.get_midi_info(path)

        assert info.tracks[1].drum_pitches == [36, 38, 42]
        assert info.tracks[0].drum_pitches == []

    def test_pitch_bend_conversion(self, tmp_path):
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        note_track = mido.MidiTrack()
        note_track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        note_track.append(mido.Message("pitchwheel", pitch=0, time=100))
        note_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        note_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(note_track)

        path = tmp_path / "bend.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)
        bend_events = [e for t in cseq.songs[0].tracks for e in t.events if e.event_type == CseqEventType.PITCH_BEND]

        assert len(bend_events) == 1
        assert 0 <= bend_events[0].pitch <= 255
