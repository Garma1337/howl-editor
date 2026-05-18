# coding: utf-8

from struct import unpack_from

from howl_editor.ctr.formats.cseq.models import CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument, CseqPercussion


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
