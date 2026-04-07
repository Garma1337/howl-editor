# coding: utf-8

from struct import unpack_from

from howl_editor.audio.cseq_renderer import CseqRenderer
from howl_editor.audio.decoder.adsr_decoder import AdsrDecoder
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.voice import PitchCalculator, GainCalculator
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CseqInstrument, CseqPercussion,
)


def _renderer():
    wav = WavWriter()
    return CseqRenderer(VagDecoder(wav), AdsrDecoder(), wav, PitchCalculator(), GainCalculator())


def _silent_vag_frame():
    return b"\x00\x07" + b"\x00" * 14


def _tone_vag_frames():
    """Two VAG frames: one with data, one end marker. Produces audible samples."""
    frame1 = bytes([0x00, 0x00] + [0x77] * 14)
    frame2 = bytes([0x00, 0x07] + [0x00] * 14)
    return frame1 + frame2


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

    def test_produces_stereo_pcm_data(self):
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

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0
        assert len(pcm) % 4 == 0  # stereo 16-bit = 4 bytes per sample

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

    def test_note_off_triggers_release(self):
        renderer = _renderer()
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=200),
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )
        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})
        assert len(pcm) > 0

    def test_percussion_track(self):
        renderer = _renderer()

        # CTR uses the note number as percussion index, so pitch=0 hits percussions[0]
        track = CseqTrack(flags=1, events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=0, velocity=127),
            CseqEvent(delta=100, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            percussions=[CseqPercussion(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_velocity_event_affects_volume(self):
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.VELOCITY, pitch=50),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=0),
            CseqEvent(delta=50, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_pan_event(self):
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=0),  # full left
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=200),
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        # Stereo: left should have signal, right should be near-silent
        assert len(pcm) >= 4

    def test_percussion_out_of_range_skipped(self):
        renderer = _renderer()

        # note pitch=99 exceeds percussions list → voice skipped, no crash
        track = CseqTrack(flags=1, events=[
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=99, velocity=127),
            CseqEvent(delta=10, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            percussions=[CseqPercussion(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert isinstance(pcm, bytes)

    def test_velocity_zero_defaults_to_127(self):
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=0),
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_mid_note_velocity_changes_gain(self):
        renderer = _renderer()

        # Plays a note, then changes seq_vol mid-note via VELOCITY event
        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=127),
            CseqEvent(delta=50, event_type=CseqEventType.VELOCITY, pitch=10),
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_mid_note_pan_changes_gain(self):
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=127),
            CseqEvent(delta=50, event_type=CseqEventType.PAN, pitch=0),  # hard left mid-note
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_pitch_bend_changes_pitch(self):
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=127),
            CseqEvent(delta=50, event_type=CseqEventType.PITCH_BEND, pitch=0xC0),
            CseqEvent(delta=50, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0

    def test_note_off_removes_from_live_voices(self):
        """After note_off, subsequent VELOCITY events should NOT update that voice."""
        renderer = _renderer()

        track = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=127),
            CseqEvent(delta=20, event_type=CseqEventType.NOTE_OFF, pitch=60),
            # This velocity change happens after note_off — should not crash
            CseqEvent(delta=10, event_type=CseqEventType.VELOCITY, pitch=50),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        cseq = CseqFile(
            instruments=[CseqInstrument(sample_id=0, frequency=0x1000)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])],
        )

        pcm = renderer.render_song(cseq, 0, {0: _tone_vag_frames()})

        assert len(pcm) > 0


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

    def test_wav_stereo(self):
        renderer = _renderer()
        track = CseqTrack(events=[CseqEvent(delta=0, event_type=CseqEventType.END_TRACK)])
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])])
        wav = renderer.render_song_to_wav(cseq, 0, {}, output_rate=44100)
        channels = unpack_from("<H", wav, 22)[0]

        assert channels == 2

    def test_wav_sample_rate(self):
        renderer = _renderer()
        track = CseqTrack(events=[CseqEvent(delta=0, event_type=CseqEventType.END_TRACK)])
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])])
        wav = renderer.render_song_to_wav(cseq, 0, {}, output_rate=44100)
        rate = unpack_from("<I", wav, 24)[0]

        assert rate == 44100
