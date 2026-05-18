# coding: utf-8

from howl_editor.ctr.audio_settings import DEFAULT_PAN
from howl_editor.ctr.voice.gain_calculator import GainCalculator


class TestGainCompute:
    def setup_method(self):
        self.calc = GainCalculator()

    def test_center_pan_gives_roughly_equal_lr(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=255, pan=DEFAULT_PAN)

        assert abs(l - r) < 0.02

    def test_full_left_pan(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=255, pan=0)

        assert l > 0
        assert r == 0.0

    def test_full_right_pan(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=255, pan=255)

        # volumeLR[0]=0x00, so L channel is silent at pan=255
        assert l == 0.0
        assert r > 0

    def test_zero_inst_vol_gives_silence(self):
        l, r = self.calc.compute(inst_vol=0, note_vel=127, seq_vol=255, pan=DEFAULT_PAN)

        assert l == 0.0
        assert r == 0.0

    def test_zero_note_vel_gives_silence(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=0, seq_vol=255, pan=DEFAULT_PAN)

        assert l == 0.0
        assert r == 0.0

    def test_zero_seq_vol_gives_silence(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=0, pan=DEFAULT_PAN)

        assert l == 0.0
        assert r == 0.0

    def test_gains_in_unit_range(self):
        l, r = self.calc.compute(inst_vol=255, note_vel=255, seq_vol=255, pan=DEFAULT_PAN)

        assert 0.0 <= l <= 1.0
        assert 0.0 <= r <= 1.0

    def test_higher_inst_vol_gives_higher_gain(self):
        l_low, _ = self.calc.compute(inst_vol=50, note_vel=127, seq_vol=255, pan=DEFAULT_PAN)
        l_high, _ = self.calc.compute(inst_vol=200, note_vel=127, seq_vol=255, pan=DEFAULT_PAN)

        assert l_high > l_low

    def test_higher_seq_vol_gives_higher_gain(self):
        l_low, _ = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=50, pan=DEFAULT_PAN)
        l_high, _ = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=200, pan=DEFAULT_PAN)

        assert l_high > l_low

    def test_pan_clamps_to_valid_range(self):
        # Should not crash with out-of-range values (clamped internally)
        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=255, pan=-10)
        assert l >= 0 and r >= 0

        l, r = self.calc.compute(inst_vol=255, note_vel=127, seq_vol=255, pan=300)
        assert l >= 0 and r >= 0
