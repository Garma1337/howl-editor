# coding: utf-8

import io

import pytest

from howl_editor.ctr.formats.cseq.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument,
)
from howl_editor.midi.exporter import CseqMidiExporter, MidiExportOptions

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

pytestmark = pytest.mark.skipif(not HAS_MIDO, reason="mido not installed")


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


def _make_velocity_cseq() -> CseqFile:
    track = CseqTrack(events=[
        CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
        CseqEvent(delta=10, event_type=CseqEventType.VELOCITY, pitch=64),
        CseqEvent(delta=20, event_type=CseqEventType.NOTE_OFF, pitch=60),
        CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
    ])

    return _make_cseq(tracks=[track])


class TestIncludeVolumeEvents:

    def test_default_emits_cc_volume(self, exporter):
        data = exporter.export(_make_velocity_cseq(), 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        volume_msgs = [
            m for m in mid.tracks[1]
            if m.type == "control_change" and m.control == 7
        ]

        assert len(volume_msgs) == 1
        # The exporter passes the CSEQ pitch byte through as-is (matching
        # the existing test_velocity_as_cc7 behaviour) — no 0-255 → 0-127 rescale.
        assert volume_msgs[0].value == 64

    def test_disabled_drops_cc_volume(self, exporter):
        options = MidiExportOptions(include_volume_events=False)
        data = exporter.export(_make_velocity_cseq(), 0, options)
        mid = mido.MidiFile(file=io.BytesIO(data))
        volume_msgs = [
            m for m in mid.tracks[1]
            if m.type == "control_change" and m.control == 7
        ]

        assert len(volume_msgs) == 0

    def test_disabled_preserves_following_note_offset(self, exporter):
        """When the VELOCITY event is dropped, its delta-time must roll into
        the next emitted message — otherwise the NOTE_OFF would arrive 10
        ticks early. (CSEQ events stack 0, +10, +20; expected next-message
        time after dropping the +10 event is 10+20 = 30.)"""
        options = MidiExportOptions(include_volume_events=False)
        data = exporter.export(_make_velocity_cseq(), 0, options)
        mid = mido.MidiFile(file=io.BytesIO(data))

        track = mid.tracks[1]
        note_offs = [m for m in track if m.type == "note_off"]

        assert len(note_offs) == 1
        assert note_offs[0].time == 30


class TestApplyInstrumentVolume:

    def _cseq_with_inst(self, inst_volume: int) -> CseqFile:
        track = CseqTrack(
            flags=0, instrument=0,
            events=[
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_OFF, pitch=60),
                CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
            ],
        )

        return CseqFile(
            instruments=[CseqInstrument(volume=inst_volume)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

    def test_default_doesnt_emit_initial_volume(self, exporter):
        data = exporter.export(self._cseq_with_inst(200), 0)
        mid = mido.MidiFile(file=io.BytesIO(data))
        # First event should be the NOTE_ON, not a CC#7.
        track = mid.tracks[1]
        first_real = next(m for m in track if not m.is_meta)

        assert first_real.type == "note_on"

    def test_enabled_emits_initial_volume(self, exporter):
        options = MidiExportOptions(apply_instrument_volume=True)
        data = exporter.export(self._cseq_with_inst(255), 0, options)
        mid = mido.MidiFile(file=io.BytesIO(data))
        track = mid.tracks[1]
        first_cc = next(
            (m for m in track if m.type == "control_change" and m.control == 7),
            None,
        )

        assert first_cc is not None
        assert first_cc.time == 0
        # inst.volume=255 → MIDI CC #7 = 127 (full).
        assert first_cc.value == 127

    def test_skips_drum_tracks(self, exporter):
        track = CseqTrack(
            flags=1, instrument=0,  # flags=1 == drum
            events=[
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=36, velocity=100),
                CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
            ],
        )
        cseq = CseqFile(
            instruments=[CseqInstrument(volume=255)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        options = MidiExportOptions(apply_instrument_volume=True)
        data = exporter.export(cseq, 0, options)
        mid = mido.MidiFile(file=io.BytesIO(data))
        cc = [m for m in mid.tracks[1] if m.type == "control_change" and m.control == 7]

        assert cc == []
