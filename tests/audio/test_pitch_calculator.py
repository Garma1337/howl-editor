# coding: utf-8

from howl_editor.audio.settings.ctr import DEFAULT_DISTORT, NOTE_FREQUENCY
from howl_editor.audio.voice import PitchCalculator


class TestInstrumentPitch:

    def setup_method(self):
        self.calc = PitchCalculator()

    def test_middle_c_default_distort_returns_base(self):
        # noteFrequency[60] = 0x1000, so freq = base_pitch * 0x1000 >> 12 = base_pitch
        # pitch_ratio = (base_pitch / 4096) * (44100 / output_rate)
        ratio = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)

        assert abs(ratio - 1.0) < 0.01

    def test_octave_up_doubles_pitch(self):
        ratio_c4 = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_c5 = self.calc.instrument(0x1000, 72, DEFAULT_DISTORT, 44100)

        assert abs(ratio_c5 / ratio_c4 - 2.0) < 0.01

    def test_octave_down_halves_pitch(self):
        ratio_c4 = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_c3 = self.calc.instrument(0x1000, 48, DEFAULT_DISTORT, 44100)

        assert abs(ratio_c4 / ratio_c3 - 2.0) < 0.01

    def test_output_rate_scales_ratio(self):
        ratio_44k = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_22k = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 22050)

        assert abs(ratio_22k / ratio_44k - 2.0) < 0.01

    def test_fine_distortion_raises_pitch(self):
        # distort=0x9F → coarse offset 0, fine=0x1F → adds a fraction of a semitone
        ratio_plain = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_bent = self.calc.instrument(0x1000, 60, 0x9F, 44100)

        assert ratio_bent > ratio_plain

    def test_coarse_distortion_shifts_note_up(self):
        # distort=0xC0 → (0xC0 >> 6) - 2 = 1 → shifts note index up by 1
        ratio_plain = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_up = self.calc.instrument(0x1000, 60, 0xC0, 44100)

        # Should be approximately one semitone higher (~1.0595x)
        assert 1.05 < ratio_up / ratio_plain < 1.07

    def test_coarse_distortion_shifts_note_down(self):
        # distort=0x40 → (0x40 >> 6) - 2 = -1 → shifts note index down by 1
        ratio_plain = self.calc.instrument(0x1000, 60, DEFAULT_DISTORT, 44100)
        ratio_down = self.calc.instrument(0x1000, 60, 0x40, 44100)

        assert ratio_down < ratio_plain

    def test_note_index_clamped_low(self):
        # Very low note + downward distort → index clamped to 0
        ratio = self.calc.instrument(0x1000, 0, 0x00, 44100)

        assert ratio > 0

    def test_note_index_clamped_high(self):
        # Very high note + upward distort → index clamped to max
        ratio = self.calc.instrument(0x1000, len(NOTE_FREQUENCY) - 1, 0xFF, 44100)

        assert ratio > 0


class TestDrumPitch:

    def setup_method(self):
        self.calc = PitchCalculator()

    def test_default_distort_is_identity(self):
        # With default distort (0x80), pitch = drum_freq unchanged
        ratio = self.calc.drum(0x1000, DEFAULT_DISTORT, 44100)

        assert abs(ratio - 1.0) < 0.01

    def test_higher_freq_gives_higher_ratio(self):
        ratio_low = self.calc.drum(0x800, DEFAULT_DISTORT, 44100)
        ratio_high = self.calc.drum(0x1000, DEFAULT_DISTORT, 44100)

        assert ratio_high > ratio_low

    def test_distort_below_center_lowers_pitch(self):
        # distortConst_OtherFX[0] = 0x8000, so pitch * 0x8000 >> 16 = pitch * 0.5
        ratio_plain = self.calc.drum(0x1000, DEFAULT_DISTORT, 44100)
        ratio_low = self.calc.drum(0x1000, 0x00, 44100)

        assert abs(ratio_low / ratio_plain - 0.5) < 0.01

    def test_distort_above_center_raises_pitch(self):
        ratio_plain = self.calc.drum(0x1000, DEFAULT_DISTORT, 44100)
        ratio_high = self.calc.drum(0x1000, 0xFF, 44100)

        assert ratio_high > ratio_plain

    def test_output_rate_scales_ratio(self):
        ratio_44k = self.calc.drum(0x1000, DEFAULT_DISTORT, 44100)
        ratio_22k = self.calc.drum(0x1000, DEFAULT_DISTORT, 22050)

        assert abs(ratio_22k / ratio_44k - 2.0) < 0.01
