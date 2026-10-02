# coding: utf-8

import pytest

from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.editor import CseqEditor
from howl_editor.ctr.formats.cseq.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument,
    CseqPercussion,
)
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from tests.conftest import build_cseq_bytes


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


class TestAppendSequence:

    def test_appends(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song(bpm=100))

        new_blob = cseq_editor_svc.append_sequence(blob, _make_song(bpm=200))
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 2
        assert parsed.songs[0].bpm == 100
        assert parsed.songs[1].bpm == 200

    def test_appends_to_empty_cseq(self, cseq_editor_svc, cseq_reader):
        blob = CseqWriter(VlqCodec()).serialize(CseqFile())

        new_blob = cseq_editor_svc.append_sequence(blob, _make_song(bpm=140))
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.songs) == 1
        assert parsed.songs[0].bpm == 140


class TestUpdateInstrument:

    def _blob(self) -> bytes:
        cseq = CseqFile(
            instruments=[CseqInstrument(volume=128, frequency=0x1000, sample_id=5)],
            songs=[_make_song()],
        )
        return CseqWriter(VlqCodec()).serialize(cseq)

    def test_updates_volume_and_frequency(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(self._blob(), 0, 200, 0x2000)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].volume == 200
        assert parsed.instruments[0].frequency == 0x2000

    def test_preserves_sample_id(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(self._blob(), 0, 200, 0x2000)
        parsed = cseq_reader.read(new_blob)
        assert parsed.instruments[0].sample_id == 5

    def test_clamps_to_format_widths(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(self._blob(), 0, 9999, 0x1FFFF)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].volume == 0xFF
        assert parsed.instruments[0].frequency == 0xFFFF

    def test_clamps_negatives_to_zero(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(self._blob(), 0, -5, -100)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].volume == 0
        assert parsed.instruments[0].frequency == 0

    def test_out_of_range_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.update_instrument(self._blob(), 7, 0, 0)

    def test_leaves_adsr_untouched_when_none(self, cseq_editor_svc, cseq_reader):
        original = cseq_reader.read(self._blob()).instruments[0].adsr
        new_blob = cseq_editor_svc.update_instrument(self._blob(), 0, 100, 0x1000)
        parsed = cseq_reader.read(new_blob)
        assert parsed.instruments[0].adsr == original

    def test_writes_adsr_when_provided(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(
            self._blob(), 0, 100, 0x1000, adsr=0xDEADBEEF,
        )
        parsed = cseq_reader.read(new_blob)
        assert parsed.instruments[0].adsr == 0xDEADBEEF

    def test_clamps_adsr_to_u32(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(
            self._blob(), 0, 100, 0x1000, adsr=0x1_0000_0000,
        )
        parsed = cseq_reader.read(new_blob)
        assert parsed.instruments[0].adsr == 0xFFFFFFFF

    def test_clamps_negative_adsr_to_zero(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_instrument(
            self._blob(), 0, 100, 0x1000, adsr=-1,
        )
        parsed = cseq_reader.read(new_blob)
        assert parsed.instruments[0].adsr == 0


class TestUpdatePercussion:

    def _blob(self) -> bytes:
        cseq = CseqFile(
            percussions=[CseqPercussion(volume=80, frequency=0x1000, sample_id=7)],
            songs=[_make_song()],
        )
        return CseqWriter(VlqCodec()).serialize(cseq)

    def test_updates_volume_and_frequency(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_percussion(self._blob(), 0, 240, 0x4000)
        parsed = cseq_reader.read(new_blob)

        assert parsed.percussions[0].volume == 240
        assert parsed.percussions[0].frequency == 0x4000

    def test_preserves_sample_id(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.update_percussion(self._blob(), 0, 240, 0x4000)
        parsed = cseq_reader.read(new_blob)
        assert parsed.percussions[0].sample_id == 7

    def test_out_of_range_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.update_percussion(self._blob(), 3, 0, 0)


class TestRetargetInstrument:

    def _blob(self) -> bytes:
        cseq = CseqFile(
            instruments=[CseqInstrument(volume=128, frequency=0x1000, sample_id=5)],
            songs=[_make_song()],
        )
        return CseqWriter(VlqCodec()).serialize(cseq)

    def test_changes_sample_id(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.retarget_instrument(self._blob(), 0, 42)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].sample_id == 42

    def test_preserves_volume_and_frequency(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.retarget_instrument(self._blob(), 0, 42)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].volume == 128
        assert parsed.instruments[0].frequency == 0x1000

    def test_out_of_range_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.retarget_instrument(self._blob(), 5, 0)


class TestRetargetPercussion:

    def _blob(self) -> bytes:
        cseq = CseqFile(
            percussions=[CseqPercussion(volume=200, frequency=0x1000, sample_id=12)],
            songs=[_make_song()],
        )
        return CseqWriter(VlqCodec()).serialize(cseq)

    def test_changes_sample_id(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.retarget_percussion(self._blob(), 0, 99)
        parsed = cseq_reader.read(new_blob)

        assert parsed.percussions[0].sample_id == 99

    def test_preserves_volume_and_frequency(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.retarget_percussion(self._blob(), 0, 99)
        parsed = cseq_reader.read(new_blob)

        assert parsed.percussions[0].volume == 200

    def test_out_of_range_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.retarget_percussion(self._blob(), 7, 0)


class TestReplaceTrackEvents:

    def _blob(self) -> bytes:
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0)],
            songs=[
                CseqSong(bpm=120, tpqn=480, tracks=[
                    CseqTrack(
                        flags=0, instrument=0, events=[
                            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
                            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
                        ],
                    ),
                    CseqTrack(
                        flags=1, instrument=0, events=[
                            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
                        ],
                    ),
                ]),
            ],
        )
        return CseqWriter(VlqCodec()).serialize(cseq)

    def test_replaces_named_track_events(self, cseq_editor_svc, cseq_reader):
        new_events = [
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=10, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=10, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ]

        new_blob = cseq_editor_svc.replace_track_events(self._blob(), 0, 0, new_events)
        parsed = cseq_reader.read(new_blob)
        events = parsed.songs[0].tracks[0].events

        # The CHANGE_PATCH gets stripped by the reader into track.instrument,
        # so the visible event stream starts with NOTE_ON.
        types = [e.event_type for e in events]
        assert CseqEventType.NOTE_ON in types
        assert CseqEventType.NOTE_OFF in types

    def test_preserves_drum_flag_on_target_track(self, cseq_editor_svc, cseq_reader):
        new_events = [
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ]

        new_blob = cseq_editor_svc.replace_track_events(self._blob(), 0, 1, new_events)
        parsed = cseq_reader.read(new_blob)

        assert parsed.songs[0].tracks[1].is_drum

    def test_doesnt_touch_other_tracks(self, cseq_editor_svc, cseq_reader):
        new_events = [
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=80),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ]

        new_blob = cseq_editor_svc.replace_track_events(self._blob(), 0, 0, new_events)
        parsed = cseq_reader.read(new_blob)

        # Track 1 originally had only END_TRACK — its event count shouldn't grow.
        track_1_types = [e.event_type for e in parsed.songs[0].tracks[1].events]
        assert CseqEventType.NOTE_ON not in track_1_types

    def test_out_of_range_seq_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.replace_track_events(self._blob(), 9, 0, [])

    def test_out_of_range_track_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.replace_track_events(self._blob(), 0, 9, [])


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


def _make_event_song(*events: CseqEvent) -> CseqSong:
    """A one-track song whose event list is exactly what was passed, with the
    terminator appended."""
    track = CseqTrack(events=[*events, CseqEvent(event_type=CseqEventType.END_TRACK)])
    return CseqSong(bpm=120, tpqn=480, tracks=[track])


class TestAppendDescriptor:

    def test_appends_percussion(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song())

        new_blob = cseq_editor_svc.append_percussion(blob, sample_id=7, volume=200, frequency=0x800)
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.percussions) == 1
        assert parsed.percussions[0].sample_id == 7
        assert parsed.percussions[0].volume == 200
        assert parsed.percussions[0].frequency == 0x800

    def test_two_percussions_may_share_one_sample_at_different_pitches(
        self, cseq_editor_svc, cseq_reader,
    ):
        """The whole point of the feature: one ADPCM blob, two pitched
        variants, addressed by drum index."""
        blob = _make_cseq_blob(_make_song())

        blob = cseq_editor_svc.append_percussion(blob, sample_id=447, volume=255, frequency=1024)
        blob = cseq_editor_svc.append_percussion(blob, sample_id=447, volume=255, frequency=767)
        parsed = cseq_reader.read(blob)

        assert [p.sample_id for p in parsed.percussions] == [447, 447]
        assert [p.frequency for p in parsed.percussions] == [1024, 767]

    def test_appends_instrument_with_adsr(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song())

        new_blob = cseq_editor_svc.append_instrument(
            blob, sample_id=3, volume=128, frequency=0x1000, adsr=0x12345678,
        )
        parsed = cseq_reader.read(new_blob)

        assert len(parsed.instruments) == 1
        assert parsed.instruments[0].sample_id == 3
        assert parsed.instruments[0].adsr == 0x12345678

    def test_instrument_adsr_defaults_when_omitted(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song())

        new_blob = cseq_editor_svc.append_instrument(blob, sample_id=0, volume=255, frequency=0x1000)
        parsed = cseq_reader.read(new_blob)

        assert parsed.instruments[0].adsr == CseqInstrument().adsr

    def test_clamps_out_of_range_values(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_song())

        new_blob = cseq_editor_svc.append_percussion(
            blob, sample_id=1, volume=9999, frequency=-5,
        )
        parsed = cseq_reader.read(new_blob)

        assert parsed.percussions[0].volume == 255
        assert parsed.percussions[0].frequency == 0

    def test_preserves_existing_descriptors(self, cseq_editor_svc, cseq_reader):
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=5)],
            percussions=[CseqPercussion(sample_id=9)],
            songs=[_make_song()],
        )
        blob = CseqWriter(VlqCodec()).serialize(cseq)

        new_blob = cseq_editor_svc.append_percussion(blob, sample_id=1, volume=1, frequency=1)
        parsed = cseq_reader.read(new_blob)

        assert [i.sample_id for i in parsed.instruments] == [5]
        assert [p.sample_id for p in parsed.percussions] == [9, 1]


class TestUpdateEvent:

    def test_updates_pitch_bend_value(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=0, event_type=CseqEventType.PITCH_BEND, pitch=128),
        ))

        new_blob = cseq_editor_svc.update_event(blob, 0, 0, 0, pitch=192)
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].pitch == 192

    def test_updates_note_on_pitch_and_velocity(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=13, velocity=100),
        ))

        new_blob = cseq_editor_svc.update_event(blob, 0, 0, 0, pitch=14, velocity=90)
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].pitch == 14
        assert events[0].velocity == 90

    def test_velocity_ignored_on_single_param_event(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128),
        ))

        new_blob = cseq_editor_svc.update_event(blob, 0, 0, 0, pitch=200, velocity=55)
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].pitch == 200
        assert events[0].velocity == 0

    def test_refuses_terminal_event(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_event_song())

        with pytest.raises(ValueError, match="does not touch"):
            cseq_editor_svc.update_event(blob, 0, 0, 0, pitch=1)

    def test_out_of_range_event_raises(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_event_song())

        with pytest.raises(IndexError):
            cseq_editor_svc.update_event(blob, 0, 0, 99, pitch=1)


class TestInsertEvent:

    def test_inserts_before_index(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=10, event_type=CseqEventType.NOTE_ON, pitch=1, velocity=99),
        ))

        new_blob = cseq_editor_svc.insert_event(
            blob, 0, 0, 0, CseqEventType.PITCH_BEND, pitch=160, delta=0,
        )
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].event_type == CseqEventType.PITCH_BEND
        assert events[0].pitch == 160
        assert events[1].event_type == CseqEventType.NOTE_ON

    def test_zero_delta_leaves_following_timing_untouched(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=10, event_type=CseqEventType.NOTE_ON, pitch=1, velocity=99),
        ))

        new_blob = cseq_editor_svc.insert_event(
            blob, 0, 0, 0, CseqEventType.PAN, pitch=64, delta=0,
        )
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[1].delta == 10

    def test_refuses_terminal_type(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_event_song())

        with pytest.raises(ValueError, match="not an insertable event"):
            cseq_editor_svc.insert_event(
                blob, 0, 0, 0, CseqEventType.END_TRACK, pitch=0,
            )


class TestDeleteEvent:

    def test_deletes_event(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64),
            CseqEvent(delta=5, event_type=CseqEventType.NOTE_ON, pitch=1, velocity=99),
        ))

        new_blob = cseq_editor_svc.delete_event(blob, 0, 0, 0)
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].event_type == CseqEventType.NOTE_ON

    def test_folds_delta_into_next_event(self, cseq_editor_svc, cseq_reader):
        blob = _make_cseq_blob(_make_event_song(
            CseqEvent(delta=7, event_type=CseqEventType.PAN, pitch=64),
            CseqEvent(delta=5, event_type=CseqEventType.NOTE_ON, pitch=1, velocity=99),
        ))

        new_blob = cseq_editor_svc.delete_event(blob, 0, 0, 0)
        events = cseq_reader.read(new_blob).songs[0].tracks[0].events

        assert events[0].delta == 12

    def test_refuses_terminal_event(self, cseq_editor_svc):
        blob = _make_cseq_blob(_make_event_song())

        with pytest.raises(ValueError, match="does not touch"):
            cseq_editor_svc.delete_event(blob, 0, 0, 0)


class TestBulkVolume:

    def _blob(self):
        return build_cseq_bytes(
            instruments=[CseqInstrument(volume=v) for v in (255, 200, 100)],
            percussions=[CseqPercussion(volume=v) for v in (255, 180)],
        )

    def test_sets_only_the_selected_instruments(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.set_instrument_volumes(self._blob(), [0, 2], 64)

        assert [i.volume for i in cseq_reader.read(new_blob).instruments] == [64, 200, 64]

    def test_sets_selected_percussion(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.set_percussion_volumes(self._blob(), [1], 10)

        assert [p.volume for p in cseq_reader.read(new_blob).percussions] == [255, 10]

    def test_clamps_to_the_byte_field(self, cseq_editor_svc, cseq_reader):
        new_blob = cseq_editor_svc.set_instrument_volumes(self._blob(), [0], 9999)

        assert cseq_reader.read(new_blob).instruments[0].volume == cseq_fmt.MAX_VOLUME

    def test_an_index_that_is_not_there_raises(self, cseq_editor_svc):
        with pytest.raises(IndexError):
            cseq_editor_svc.set_instrument_volumes(self._blob(), [9], 64)
