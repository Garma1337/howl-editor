# coding: utf-8

from struct import unpack_from

from howl_editor.ctr.formats.cseq.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument, CseqPercussion
)


class TestSerializeMinimal:

    def test_produces_bytes(self, cseq_writer):
        cseq = CseqFile(songs=[
            CseqSong(tracks=[CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])])
        ])

        data = cseq_writer.serialize(cseq)

        assert isinstance(data, bytes)
        assert len(data) >= 8

    def test_file_size_field(self, cseq_writer):
        cseq = CseqFile(songs=[
            CseqSong(tracks=[CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])])
        ])

        data = cseq_writer.serialize(cseq)
        stored_size = unpack_from("<I", data, 0)[0]

        assert stored_size == len(data)

    def test_header_counts(self, cseq_writer):
        cseq = CseqFile(
            instruments=[CseqInstrument(), CseqInstrument()],
            percussions=[CseqPercussion()],
            songs=[CseqSong(tracks=[CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])])],
        )

        data = cseq_writer.serialize(cseq)
        _, num_inst, num_perc, num_songs = unpack_from("<IBBh", data, 0)

        assert num_inst == 2
        assert num_perc == 1
        assert num_songs == 1


class TestCseqRoundTrip:

    def test_minimal_roundtrip(self, cseq_reader, cseq_writer):
        original = CseqFile(songs=[
            CseqSong(bpm=120, tpqn=480, tracks=[
                CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
            ])
        ])

        data = cseq_writer.serialize(original)
        parsed = cseq_reader.read(data)

        assert len(parsed.songs) == 1
        assert parsed.songs[0].bpm == 120
        assert parsed.songs[0].tpqn == 480

    def test_with_instruments_roundtrip(self, cseq_reader, cseq_writer):
        original = CseqFile(
            instruments=[CseqInstrument(volume=200, sample_id=42, adsr=0xDEADBEEF)],
            percussions=[CseqPercussion(volume=100, sample_id=7)],
            songs=[CseqSong(tracks=[
                CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
            ])],
        )

        data = cseq_writer.serialize(original)
        parsed = cseq_reader.read(data)

        assert parsed.instruments[0].volume == 200
        assert parsed.instruments[0].sample_id == 42
        assert parsed.instruments[0].adsr == 0xDEADBEEF
        assert parsed.percussions[0].sample_id == 7

    def test_with_events_roundtrip(self, cseq_reader, cseq_writer):
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=480, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        original = CseqFile(songs=[CseqSong(bpm=140, tpqn=480, tracks=[track])])
        data = cseq_writer.serialize(original)
        parsed = cseq_reader.read(data)
        events = parsed.songs[0].tracks[0].events

        assert events[0].event_type == CseqEventType.CHANGE_PATCH
        assert events[1].event_type == CseqEventType.NOTE_ON
        assert events[1].pitch == 60
        assert events[1].velocity == 100
        assert events[2].delta == 480
        assert events[2].event_type == CseqEventType.NOTE_OFF

    def test_multiple_tracks_roundtrip(self, cseq_reader, cseq_writer):
        t1 = CseqTrack(flags=0, events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        t2 = CseqTrack(flags=1, events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        original = CseqFile(songs=[CseqSong(tracks=[t1, t2])])
        data = cseq_writer.serialize(original)
        parsed = cseq_reader.read(data)

        assert len(parsed.songs[0].tracks) == 2
        assert not parsed.songs[0].tracks[0].is_drum
        assert parsed.songs[0].tracks[1].is_drum


def _notes_track(instrument: int, note_count: int) -> CseqTrack:
    """A track with a CHANGE_PATCH, `note_count` note on/off pairs, and an
    END_TRACK — enough events that a misaligned track block truncates it."""
    events = [CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=instrument)]

    for i in range(note_count):
        events.append(CseqEvent(delta=48, event_type=CseqEventType.NOTE_ON, pitch=60 + i, velocity=100))
        events.append(CseqEvent(delta=24, event_type=CseqEventType.NOTE_OFF, pitch=60 + i))

    events.append(CseqEvent(delta=0, event_type=CseqEventType.END_TRACK))
    return CseqTrack(flags=1, events=events, instrument=instrument)


def _notes_song(bpm: int, num_tracks: int) -> CseqSong:
    return CseqSong(bpm=bpm, tpqn=480, tracks=[_notes_track(t, 3 + t) for t in range(num_tracks)])


class TestMultiSequenceRoundTrip:
    """Regression guard for the writer track-block alignment. A mask song
    (songs 0–27) holds three sub-songs — main music, Aku Aku mask, Uka Uka
    mask. Every sub-song after the first begins at an unaligned absolute
    position, so padding the track block song-relative (instead of to the
    file's ALIGNMENT boundary the reader expects) truncated the later
    sequences and silently destroyed the masks."""

    def _event_counts(self, cseq: CseqFile) -> list[list[int]]:
        return [[len(t.events) for t in s.tracks] for s in cseq.songs]

    def test_three_sequences_preserve_all_events(self, cseq_reader, cseq_writer):
        original = CseqFile(songs=[
            _notes_song(120, 3), _notes_song(130, 3), _notes_song(140, 3),
        ])

        parsed = cseq_reader.read(cseq_writer.serialize(original))

        assert self._event_counts(parsed) == self._event_counts(original)

    def test_serialize_is_idempotent_across_two_cycles(self, cseq_reader, cseq_writer):
        original = CseqFile(songs=[
            _notes_song(120, 4), _notes_song(130, 4), _notes_song(140, 4),
        ])

        once = cseq_reader.read(cseq_writer.serialize(original))
        twice = cseq_reader.read(cseq_writer.serialize(once))

        assert self._event_counts(twice) == self._event_counts(original)

    def test_mask_layout_track_counts_survive(self, cseq_reader, cseq_writer):
        # Main music with 20 tracks (the Adventure-Hub / dense-track case),
        # plus the two shorter mask sequences.
        original = CseqFile(songs=[
            _notes_song(120, 20), _notes_song(130, 4), _notes_song(140, 4),
        ])

        parsed = cseq_reader.read(cseq_writer.serialize(original))

        assert [len(s.tracks) for s in parsed.songs] == [20, 4, 4]
        assert self._event_counts(parsed) == self._event_counts(original)
