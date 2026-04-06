# coding: utf-8

from struct import unpack_from

from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CseqInstrument, CseqPercussion,
)
from howl_editor.audio.vag_decoder import VagDecoder
from howl_editor.audio.cseq_renderer import CseqRenderer


def _renderer():
    return CseqRenderer(VagDecoder())


def _silent_vag_frame():
    return b"\x00\x07" + b"\x00" * 14


class TestRenderSong:
    def test_empty_song_produces_empty(self):
        renderer = _renderer()
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[])])
        pcm = renderer.render_song(cseq, 0, {})
        assert pcm == b""

    def test_invalid_song_index(self):
        renderer = _renderer()
        cseq = CseqFile(songs=[])
        pcm = renderer.render_song(cseq, 0, {})
        assert pcm == b""

    def test_produces_pcm_data(self):
        renderer = _renderer()
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=127),
            CseqEvent(delta=120, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )
        pcm = renderer.render_song(cseq, 0, {0: _silent_vag_frame()})
        assert len(pcm) > 0

    def test_missing_sample_graceful(self):
        renderer = _renderer()
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=10, event_type=CseqEventType.END_TRACK),
        ])
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=99)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )
        pcm = renderer.render_song(cseq, 0, {})
        assert isinstance(pcm, bytes)


class TestRenderSongToWav:
    def test_wav_header(self):
        renderer = _renderer()
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])])
        wav = renderer.render_song_to_wav(cseq, 0, {})
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_wav_sample_rate(self):
        renderer = _renderer()
        track = CseqTrack(events=[CseqEvent(delta=0, event_type=CseqEventType.END_TRACK)])
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])])
        wav = renderer.render_song_to_wav(cseq, 0, {}, output_rate=44100)
        rate = unpack_from("<I", wav, 24)[0]
        assert rate == 44100
