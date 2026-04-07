# coding: utf-8

import pytest

from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.editor import CseqEditor
from howl_editor.cseq.writer import CseqWriter
from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CseqInstrument,
)


@pytest.fixture
def cseq_editor_svc(cseq_reader, cseq_writer):
    return CseqEditor(cseq_reader, cseq_writer)


def _make_song(bpm: int = 120, num_tracks: int = 1) -> CseqSong:
    tracks = [
        CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        for _ in range(num_tracks)
    ]

    return CseqSong(bpm=bpm, tpqn=480, tracks=tracks)


def _make_cseq_blob(*songs: CseqSong) -> bytes:
    cseq = CseqFile(songs=list(songs))
    return CseqWriter(VlqCodec()).serialize(cseq)


class TestReplaceSequence:

    def test_replaces_sequence(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100), _make_song(bpm=200))
        replacement = _make_song(bpm=999)

        new_blob = cseq_editor_svc.replace_sequence(blob, 1, replacement)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 2
        assert parsed.songs[0].bpm == 100
        assert parsed.songs[1].bpm == 999

    def test_preserves_other_sequences(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=10), _make_song(bpm=20), _make_song(bpm=30))
        replacement = _make_song(bpm=99)

        new_blob = cseq_editor_svc.replace_sequence(blob, 0, replacement)
        parsed = cseq_reader.read(new_blob)

        assert parsed.songs[0].bpm == 99
        assert parsed.songs[1].bpm == 20
        assert parsed.songs[2].bpm == 30

    def test_out_of_range_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.replace_sequence(blob, 5, _make_song())

    def test_negative_index_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.replace_sequence(blob, -1, _make_song())

    def test_preserves_instruments(self, cseq_editor_svc, cseq_reader):
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=42)],
            songs=[_make_song(bpm=100)],
        )

        blob = CseqWriter(VlqCodec()).serialize(cseq)
        new_blob = cseq_editor_svc.replace_sequence(blob, 0, _make_song(bpm=200))
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].sample_id == 42
        assert parsed.songs[0].bpm == 200


class TestRemoveSequence:

    def test_removes_sequence(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100), _make_song(bpm=200), _make_song(bpm=300))

        new_blob = cseq_editor_svc.remove_sequence(blob, 1)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 2
        assert parsed.songs[0].bpm == 100
        assert parsed.songs[1].bpm == 300

    def test_removes_first(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=10), _make_song(bpm=20))

        new_blob = cseq_editor_svc.remove_sequence(blob, 0)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 1
        assert parsed.songs[0].bpm == 20

    def test_removes_last(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=10), _make_song(bpm=20))

        new_blob = cseq_editor_svc.remove_sequence(blob, 1)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 1
        assert parsed.songs[0].bpm == 10

    def test_out_of_range_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.remove_sequence(blob, 3)

    def test_negative_index_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.remove_sequence(blob, -1)


class TestMoveSequence:

    def test_moves_forward(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100), _make_song(bpm=200), _make_song(bpm=300))

        new_blob = cseq_editor_svc.move_sequence(blob, 0, 2)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 3
        assert parsed.songs[0].bpm == 200
        assert parsed.songs[1].bpm == 300
        assert parsed.songs[2].bpm == 100

    def test_moves_backward(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100), _make_song(bpm=200), _make_song(bpm=300))

        new_blob = cseq_editor_svc.move_sequence(blob, 2, 0)
        parsed = cseq_reader.read(new_blob)

        assert parsed.songs[0].bpm == 300
        assert parsed.songs[1].bpm == 100
        assert parsed.songs[2].bpm == 200

    def test_same_position_is_noop(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100), _make_song(bpm=200))

        new_blob = cseq_editor_svc.move_sequence(blob, 1, 1)
        parsed = cseq_reader.read(new_blob)

        assert parsed.songs[0].bpm == 100
        assert parsed.songs[1].bpm == 200

    def test_out_of_range_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.move_sequence(blob, 0, 5)

    def test_negative_index_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.move_sequence(blob, -1, 0)
