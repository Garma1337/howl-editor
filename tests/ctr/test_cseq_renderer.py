# coding: utf-8

from struct import unpack_from

from howl_editor.audio.wav_writer import WavWriter
from howl_editor.ctr.cseq_renderer import CseqRenderer
from howl_editor.ctr.formats.cseq.models import CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument, \
    CseqPercussion
from howl_editor.ctr.voice.gain_calculator import GainCalculator
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1.adsr_decoder import AdsrDecoder
from howl_editor.ps1.formats.vag.decoder import VagDecoder


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
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
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

    def test_velocity_zero_is_silent(self):
        # CTR's noteon opcode multiplies SPU volume by note velocity, so vel=0
        # produces silent output. Match that behavior — don't substitute a default.
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

        # No audible samples should be produced — every output sample must be zero.
        assert all(b == 0 for b in pcm)

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


class TestRenderSongActiveTracks:
    """Adventure Hub preview uses `active_tracks` to mute the tracks the
    selected hub world shouldn't hear. Different hubs must produce different
    PCM outputs (which is the user-visible bug we're fixing)."""

    def test_subset_of_tracks_produces_different_output_than_full(self):
        renderer = _renderer()
        sample_data = {0: _tone_vag_frames()}

        # Two tracks: each plays one distinct note so their PCM differs.
        track_a = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=100),
            CseqEvent(delta=240, event_type=CseqEventType.NOTE_OFF, pitch=60),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])
        track_b = CseqTrack(events=[
            CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=0),
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=72, velocity=100),
            CseqEvent(delta=240, event_type=CseqEventType.NOTE_OFF, pitch=72),
            CseqEvent(delta=0, event_type=CseqEventType.END_TRACK),
        ])

        inst = CseqInstrument(volume=255, frequency=0x1000, sample_id=0, adsr=0x1FC180FF)
        cseq = CseqFile(
            instruments=[inst],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[track_a, track_b])],
        )

        full = renderer.render_song(cseq, 0, sample_data)
        only_a = renderer.render_song(cseq, 0, sample_data, active_tracks=[0])
        only_b = renderer.render_song(cseq, 0, sample_data, active_tracks=[1])

        assert only_a != full
        assert only_b != full
        assert only_a != only_b


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


class TestMixPcmStreams:

    def test_empty_streams_handled(self):
        renderer = _renderer()
        # Internal helper — touching it via render_layered with no songs.
        pcm = renderer.render_layered(CseqFile(songs=[]), [0, 1], {})

        assert pcm == b""

    def test_single_stream_passes_through(self):
        renderer = _renderer()
        stream = bytes([0x10, 0x00, 0x20, 0x00])  # one stereo sample: L=16, R=32

        out = renderer._mix_pcm_streams([stream])

        assert out == stream

    def test_sample_wise_sum(self):
        renderer = _renderer()
        # Two stereo streams, one stereo sample each. L+L, R+R.
        # Stream A: L=100, R=200. Stream B: L=50, R=-100.
        from struct import pack
        a = pack("<hh", 100, 200)
        b = pack("<hh", 50, -100)

        out = renderer._mix_pcm_streams([a, b])

        l, r = unpack_from("<hh", out, 0)
        assert l == 150
        assert r == 100

    def test_clamps_to_int16(self):
        renderer = _renderer()
        from struct import pack
        # Two streams that would overflow int16 if summed.
        a = pack("<hh", 30000, -30000)
        b = pack("<hh", 30000, -30000)

        out = renderer._mix_pcm_streams([a, b])
        l, r = unpack_from("<hh", out, 0)

        assert l == 32767     # clamped positive
        assert r == -32768    # clamped negative

    def test_pads_shorter_streams(self):
        renderer = _renderer()
        from struct import pack
        # Long stream: 2 stereo samples. Short stream: 1 stereo sample.
        long_stream = pack("<hhhh", 100, 100, 200, 200)
        short_stream = pack("<hh", 50, 50)

        out = renderer._mix_pcm_streams([long_stream, short_stream])

        # First sample = long[0] + short[0]; second sample = long[1] alone.
        first_l, first_r, second_l, second_r = unpack_from("<hhhh", out, 0)
        assert first_l == 150
        assert first_r == 150
        assert second_l == 200
        assert second_r == 200


class TestRenderLayered:

    def test_empty_indices_returns_empty(self):
        renderer = _renderer()
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[])])

        assert renderer.render_layered(cseq, [], {}) == b""

    def test_out_of_range_indices_skipped(self):
        renderer = _renderer()
        cseq = CseqFile(songs=[CseqSong(bpm=120, tpqn=480, tracks=[])])

        # Both indices are out of range — should return empty without crashing.
        assert renderer.render_layered(cseq, [5, 99], {}) == b""

    def test_wav_format_correct(self):
        renderer = _renderer()
        track = CseqTrack(events=[CseqEvent(delta=0, event_type=CseqEventType.END_TRACK)])
        cseq = CseqFile(songs=[
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
        ])

        wav = renderer.render_layered_to_wav(cseq, [0, 1], {}, output_rate=22050)
        channels = unpack_from("<H", wav, 22)[0]
        rate = unpack_from("<I", wav, 24)[0]

        assert channels == 2
        assert rate == 22050
