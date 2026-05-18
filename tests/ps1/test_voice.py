# coding: utf-8

from howl_editor.ps1.adsr_decoder import AdsrEnvelope
from howl_editor.ps1.voice import Voice


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
        gain_l=0.5,
        gain_r=0.5,
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


class TestVoiceGain:

    def test_gain_stored(self):
        voice = _make_voice()

        assert voice.gain_l == 0.5
        assert voice.gain_r == 0.5

    def test_gain_mutable(self):
        voice = _make_voice()
        voice.gain_l = 0.0
        voice.gain_r = 1.0

        assert voice.gain_l == 0.0
        assert voice.gain_r == 1.0


class TestVoiceMetadata:
    def test_metadata_defaults(self):
        voice = _make_voice()

        assert voice.inst_vol == 0
        assert voice.note_vel == 0
        assert voice.base_pitch == 0
        assert voice.note_index == 0
        assert voice.is_drum is False
        assert voice.output_rate == 22050

    def test_metadata_preserved(self):
        voice = Voice(
            samples=[100] * 10,
            loop_start=-1,
            pitch_ratio=1.0,
            gain_l=0.5,
            gain_r=0.5,
            envelope=_default_envelope(),
            inst_vol=200,
            note_vel=127,
            base_pitch=0x1000,
            note_index=60,
            is_drum=True,
            output_rate=44100,
        )

        assert voice.inst_vol == 200
        assert voice.note_vel == 127
        assert voice.base_pitch == 0x1000
        assert voice.note_index == 60
        assert voice.is_drum is True
        assert voice.output_rate == 44100


class TestVoiceReadInactive:

    def test_read_returns_zero_when_done(self):
        voice = _make_voice(samples=[100, 200], loop_start=-1)

        # Exhaust samples
        for _ in range(5):
            voice.read()

        assert voice.is_done()
        assert voice.read() == 0

    def test_read_returns_zero_after_release(self):
        env = AdsrEnvelope(attack_time=0.001, decay_time=0.001, sustain_level=0.5, release_time=0.001)
        voice = _make_voice(envelope=env)

        # Advance through full envelope cycle
        for _ in range(100):
            voice.advance_envelope(0.001)

        voice.note_off()
        for _ in range(100):
            voice.advance_envelope(0.001)

        assert voice.is_done()
        assert voice.read() == 0


class TestVoiceInterpolation:

    def test_interpolates_between_samples(self):
        voice = _make_voice(samples=[0, 1000, 0], pitch_ratio=0.5)
        # pos=0 → sample 0 (value 0)
        s0 = voice.read()  # reads at pos=0, advances to 0.5
        assert s0 == 0

        # pos=0.5 → interpolate between samples[0]=0 and samples[1]=1000
        s1 = voice.read()  # reads at pos=0.5, advances to 1.0
        assert abs(s1 - 500) < 2
