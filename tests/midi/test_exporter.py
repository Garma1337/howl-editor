# coding: utf-8

import io

import pytest

from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
)

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

pytestmark = pytest.mark.skipif(not HAS_MIDO, reason="mido not installed")

from howl_editor.midi.exporter import CseqMidiExporter


@pytest.fixture
def exporter():
    return CseqMidiExporter()


def _make_cseq(tracks=None, bpm=120, tpqn=480):
    if tracks is None:
        tracks = [CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])]
    return CseqFile(songs=[CseqSong(bpm=bpm, tpqn=tpqn, tracks=tracks)])


class TestExport:
    def test_produces_midi_bytes(self, exporter):
        cseq = _make_cseq()
        data = exporter.export(cseq, 0)
        assert data[:4] == b"MThd"

    def test_preserves_tpqn(self, exporter):
        cseq = _make_cseq(tpqn=240)
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        assert mid.ticks_per_beat == 240

    def test_preserves_bpm(self, exporter):
        cseq = _make_cseq(bpm=140)
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        tempo_msgs = [m for t in mid.tracks for m in t if m.type == "set_tempo"]
        assert len(tempo_msgs) == 1
        assert mido.tempo2bpm(tempo_msgs[0].tempo) == pytest.approx(140, abs=1)

    def test_invalid_song_index(self, exporter):
        cseq = _make_cseq()
        with pytest.raises(ValueError):
            exporter.export(cseq, 5)


class TestNoteEvents:
    def test_note_on_off_roundtrip(self, exporter):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=480, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = _make_cseq(tracks=[track])
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))

        note_track = mid.tracks[1]
        note_on = [m for m in note_track if m.type == "note_on"]
        note_off = [m for m in note_track if m.type == "note_off"]
        assert len(note_on) == 1
        assert note_on[0].note == 60
        assert note_on[0].velocity == 100
        assert len(note_off) == 1
        assert note_off[0].note == 60

    def test_change_patch(self, exporter):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=5),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = _make_cseq(tracks=[track])
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        pc = [m for m in mid.tracks[1] if m.type == "program_change"]
        assert len(pc) == 1
        assert pc[0].program == 5


class TestDrumChannel:
    def test_drum_track_uses_channel_9(self, exporter):
        drum_track = CseqTrack(
            flags=1,
            events=[
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=36, velocity=80),
                CseqEvent(delta=100, event_type=CseqEventType.NOTE_OFF, pitch=36),
                CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
            ],
        )
        cseq = _make_cseq(tracks=[drum_track])
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        notes = [m for m in mid.tracks[1] if m.type == "note_on"]
        assert all(n.channel == 9 for n in notes)

    def test_melodic_track_avoids_channel_9(self, exporter):
        tracks = [
            CseqTrack(events=[CseqEvent(delta=0, event_type=CseqEventType.END_TRACK)])
            for _ in range(12)
        ]
        cseq = _make_cseq(tracks=tracks)
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        for track in mid.tracks[1:]:
            for msg in track:
                if hasattr(msg, "channel"):
                    assert msg.channel != 9


class TestControlEvents:
    def test_velocity_as_cc7(self, exporter):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.VELOCITY, pitch=100),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = _make_cseq(tracks=[track])
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        cc = [m for m in mid.tracks[1] if m.type == "control_change" and m.control == 7]
        assert len(cc) == 1
        assert cc[0].value == 100

    def test_pan_as_cc10(self, exporter):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = _make_cseq(tracks=[track])
        data = exporter.export(cseq, 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        cc = [m for m in mid.tracks[1] if m.type == "control_change" and m.control == 10]
        assert len(cc) == 1
        assert cc[0].value == 64
