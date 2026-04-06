# coding: utf-8

from howl_editor.audio.decoder.adsr_decoder import AdsrEnvelope
from howl_editor.audio.voice import Voice


def _default_envelope():
    return AdsrEnvelope(
        attack_time=0.01,
        decay_time=0.01,
        sustain_level=0.8,
        release_time=0.05,
    )


def _make_voice(samples=None, loop_start=-1, pitch_ratio=1.0, envelope=None):
    if samples is None:
        samples = [1000] * 100
    if envelope is None:
        envelope = _default_envelope()
    return Voice(
        samples=samples,
        loop_start=loop_start,
        pitch_ratio=pitch_ratio,
        volume=1.0,
        pan=64.0,
        velocity=1.0,
        envelope=envelope,
    )


class TestVoicePlayback:
    def test_reads_samples(self):
        voice = _make_voice(samples=[100, 200, 300])
        assert voice.read() == 100
        assert abs(voice.read() - 200) < 2
        assert abs(voice.read() - 300) < 2

    def test_done_after_samples_exhausted(self):
        voice = _make_voice(samples=[100, 200])
        voice.read()
        voice.read()
        voice.read()  # past end
        assert voice.is_done()

    def test_pitch_ratio_speeds_playback(self):
        voice = _make_voice(samples=[100] * 10, pitch_ratio=2.0)
        voice.read()
        assert voice.pos == 2.0

    def test_loop_wraps_around(self):
        samples = [100, 200, 300, 400, 500]
        voice = _make_voice(samples=samples, loop_start=2)
        for _ in range(10):
            voice.read()
        assert not voice.is_done()

    def test_no_loop_stops(self):
        voice = _make_voice(samples=[100, 200], loop_start=-1)
        for _ in range(5):
            voice.read()
        assert voice.is_done()


class TestVoiceEnvelope:
    def test_attack_phase(self):
        voice = _make_voice()
        assert voice.env_phase == Voice.PHASE_ATTACK
        level = voice.advance_envelope(0.005)
        assert level > 0

    def test_envelope_reaches_sustain(self):
        env = AdsrEnvelope(attack_time=0.001, decay_time=0.001, sustain_level=0.5, release_time=0.1)
        voice = _make_voice(envelope=env)
        for _ in range(1000):
            voice.advance_envelope(0.001)
        assert voice.env_phase == Voice.PHASE_SUSTAIN
        assert abs(voice.env_level - 0.5) < 0.1

    def test_note_off_triggers_release(self):
        voice = _make_voice()
        for _ in range(1000):
            voice.advance_envelope(0.001)
        voice.note_off()
        assert voice.env_phase == Voice.PHASE_RELEASE

    def test_release_deactivates_voice(self):
        env = AdsrEnvelope(attack_time=0.001, decay_time=0.001, sustain_level=0.5, release_time=0.01)
        voice = _make_voice(envelope=env)
        for _ in range(100):
            voice.advance_envelope(0.001)
        voice.note_off()
        for _ in range(1000):
            voice.advance_envelope(0.001)
        assert voice.is_done()

    def test_sustain_decrease(self):
        env = AdsrEnvelope(
            attack_time=0.001, decay_time=0.001, sustain_level=1.0,
            release_time=0.1, sustain_shift=5, sustain_decrease=True,
        )
        voice = _make_voice(envelope=env)
        for _ in range(100):
            voice.advance_envelope(0.001)
        assert voice.env_phase == Voice.PHASE_SUSTAIN
        initial = voice.env_level
        for _ in range(1000):
            voice.advance_envelope(0.001)
        assert voice.env_level < initial


class TestVoicePan:
    def test_pan_stored(self):
        voice = _make_voice()
        voice.pan = 0.0
        assert voice.pan == 0.0

    def test_default_pan_center(self):
        voice = _make_voice()
        assert voice.pan == 64.0
