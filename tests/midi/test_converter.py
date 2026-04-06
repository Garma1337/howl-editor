# coding: utf-8

import tempfile
from pathlib import Path

import pytest

from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.models import MidiConvertSettings, InstrumentMapping

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

pytestmark = pytest.mark.skipif(not HAS_MIDO, reason="mido not installed")


def _converter():
    vlq = VlqCodec()
    return MidiConverter(CseqWriter(vlq))


def _reader():
    return CseqReader(VlqCodec())


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
        from howl_editor.models import CseqEventType
        bend_events = [e for t in cseq.songs[0].tracks for e in t.events if e.event_type == CseqEventType.PITCH_BEND]
        assert len(bend_events) == 1
        assert 0 <= bend_events[0].pitch <= 255
