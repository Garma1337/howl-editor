# coding: utf-8

from struct import pack, unpack

from howl_editor.audio.linear_interpolation_resampler import LinearInterpolationResampler


def _pcm(values: list[int]) -> bytes:
    return pack(f"<{len(values)}h", *values)


def _samples(pcm: bytes) -> tuple[int, ...]:
    return unpack(f"<{len(pcm) // 2}h", pcm)


class TestLinearInterpolationResampler:

    def test_same_rate_returns_input_unchanged(self):
        resampler = LinearInterpolationResampler()
        pcm = _pcm([0, 100, -100, 200])

        assert resampler.resample(pcm, 11025, 11025) == pcm

    def test_empty_input_returns_empty(self):
        resampler = LinearInterpolationResampler()

        assert resampler.resample(b"", 7000, 11025) == b""

    def test_invalid_rates_return_input(self):
        resampler = LinearInterpolationResampler()
        pcm = _pcm([0, 100])

        assert resampler.resample(pcm, 0, 11025) == pcm
        assert resampler.resample(pcm, 11025, -1) == pcm

    def test_upsample_doubles_sample_count(self):
        resampler = LinearInterpolationResampler()
        pcm = _pcm([0, 1000])

        out = resampler.resample(pcm, 4000, 8000)

        assert len(_samples(out)) == 4

    def test_downsample_halves_sample_count(self):
        resampler = LinearInterpolationResampler()
        pcm = _pcm([0, 100, 200, 300])

        out = resampler.resample(pcm, 8000, 4000)

        assert len(_samples(out)) == 2

    def test_linear_interpolation_midpoint(self):
        resampler = LinearInterpolationResampler()
        pcm = _pcm([0, 1000])

        out = _samples(resampler.resample(pcm, 4000, 8000))

        # Doubling rate: out[0] sits at src index 0, out[1] at src index 0.5
        # — linear interp gives (0 + 1000) / 2 = 500.
        assert out[0] == 0
        assert out[1] == 500

    def test_preserves_audible_duration(self):
        """A 1-second 4 kHz clip resampled to 8 kHz should still produce
        ~1 second of audio (2× as many samples)."""
        resampler = LinearInterpolationResampler()
        pcm = _pcm([i % 1000 for i in range(4000)])

        out = resampler.resample(pcm, 4000, 8000)

        assert abs(len(_samples(out)) - 8000) <= 1
