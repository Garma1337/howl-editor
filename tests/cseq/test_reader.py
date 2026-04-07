# coding: utf-8

import pytest

from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CseqInstrument, CseqPercussion, CseqInfo,
)
from tests.conftest import build_cseq_bytes


class TestValidation:

    def test_too_small_raises(self, cseq_reader):
        with pytest.raises(ValueError, match="too small"):
            cseq_reader.read(b"\x00" * 4)


class TestGetInfo:

    def test_returns_cseq_info(self, cseq_reader):
        data = build_cseq_bytes()
        info = cseq_reader.get_info(data)

        assert isinstance(info, CseqInfo)
        assert info.num_songs == 1

    def test_too_small_returns_empty(self, cseq_reader):
        info = cseq_reader.get_info(b"\x00")

        assert info.file_size == 0

    def test_with_instruments(self, cseq_reader):
        data = build_cseq_bytes(instruments=[CseqInstrument(sample_id=5)])
        info = cseq_reader.get_info(data)

        assert info.num_instruments == 1


class TestReadMinimal:

    def test_minimal_cseq(self, cseq_reader):
        data = build_cseq_bytes()
        cseq = cseq_reader.read(data)

        assert isinstance(cseq, CseqFile)
        assert len(cseq.songs) == 1
        assert len(cseq.songs[0].tracks) == 1

    def test_end_track_event(self, cseq_reader):
        data = build_cseq_bytes()
        cseq = cseq_reader.read(data)
        track = cseq.songs[0].tracks[0]

        assert any(e.event_type == CseqEventType.END_TRACK for e in track.events)


class TestReadInstruments:

    def test_parses_instruments(self, cseq_reader):
        instruments = [
            CseqInstrument(flags=1, volume=200, frequency=0x2000, sample_id=10, adsr=0xAABBCCDD),
        ]

        data = build_cseq_bytes(instruments=instruments)
        cseq = cseq_reader.read(data)

        assert len(cseq.instruments) == 1
        assert cseq.instruments[0].volume == 200
        assert cseq.instruments[0].sample_id == 10
        assert cseq.instruments[0].adsr == 0xAABBCCDD

    def test_parses_percussions(self, cseq_reader):
        percussions = [CseqPercussion(flags=1, volume=100, frequency=0x800, sample_id=5)]
        data = build_cseq_bytes(percussions=percussions)
        cseq = cseq_reader.read(data)

        assert len(cseq.percussions) == 1
        assert cseq.percussions[0].sample_id == 5


class TestReadEvents:

    def test_note_on_event(self, cseq_reader):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=10, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        song = CseqSong(tracks=[track])
        data = build_cseq_bytes(songs=[song])
        cseq = cseq_reader.read(data)
        events = cseq.songs[0].tracks[0].events

        assert events[0].event_type == CseqEventType.NOTE_ON
        assert events[0].pitch == 60
        assert events[0].velocity == 100

    def test_change_patch_sets_instrument(self, cseq_reader):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=3),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        song = CseqSong(tracks=[track])
        data = build_cseq_bytes(songs=[song])
        cseq = cseq_reader.read(data)

        assert cseq.songs[0].tracks[0].instrument == 3


class TestReadSongMetadata:

    def test_bpm_and_tpqn(self, cseq_reader):
        song = CseqSong(bpm=140, tpqn=240, tracks=[
            CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        ])

        data = build_cseq_bytes(songs=[song])
        cseq = cseq_reader.read(data)

        assert cseq.songs[0].bpm == 140
        assert cseq.songs[0].tpqn == 240


class TestGetName:

    def test_known_song(self, cseq_reader):
        assert cseq_reader.get_name(0) == "Dingo Canyon"
        assert cseq_reader.get_name(25) == "Boss Race"
        assert cseq_reader.get_name(32) == "Credits"

    def test_unknown_song(self, cseq_reader):
        assert cseq_reader.get_name(99) == "Custom"

    def test_custom_threshold(self, cseq_reader):
        assert cseq_reader.get_name(33) == "Custom"
        assert cseq_reader.get_name(32) != "Custom"


class TestAlignTo:

    def test_already_aligned(self, cseq_reader):
        assert cseq_reader._align_to(8, 4) == 8

    def test_needs_alignment(self, cseq_reader):
        assert cseq_reader._align_to(9, 4) == 12

    def test_zero_aligned(self, cseq_reader):
        assert cseq_reader._align_to(0, 4) == 0
