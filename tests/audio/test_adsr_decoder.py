# coding: utf-8

from howl_editor.audio.decoder.adsr_decoder import AdsrDecoder, AdsrEnvelope


class TestAdsrDecoder:

    def test_default_instrument_adsr(self):
        decoder = AdsrDecoder()
        env = decoder.decode(0x1FC180FF)

        assert isinstance(env, AdsrEnvelope)
        assert env.attack_time > 0
        assert env.decay_time >= 0
        assert 0.0 <= env.sustain_level <= 1.0
        assert env.release_time > 0

    def test_percussion_adsr(self):
        decoder = AdsrDecoder()
        # CTR hardcoded: ad=0x80FF, sr=0x1FC2
        # SL=15 (max), DR=15 (fast decay to sustain), AR=0 (slow, but samples are short)
        env = decoder.decode(0x1FC280FF)

        assert env.sustain_level == 1.0

    def test_zero_adsr(self):
        decoder = AdsrDecoder()
        env = decoder.decode(0x00000000)

        assert env.attack_time >= 0
        assert env.release_time >= 0

    def test_max_adsr(self):
        decoder = AdsrDecoder()
        env = decoder.decode(0xFFFFFFFF)

        assert env.attack_time <= 5.0
        assert env.decay_time <= 5.0
        assert env.release_time <= 5.0

    def test_sustain_level_range(self):
        decoder = AdsrDecoder()
        env_low = decoder.decode(0x00000000)  # sustain_level_raw = 0
        env_high = decoder.decode(0x0000000F)  # sustain_level_raw = 15

        assert env_low.sustain_level < env_high.sustain_level
        assert env_high.sustain_level == 1.0

    def test_sustain_decrease_flag(self):
        decoder = AdsrDecoder()
        env_inc = decoder.decode(0x00000000)
        env_dec = decoder.decode(0x40000000)  # bit 14 of SR = sustain dir

        assert not env_inc.sustain_decrease
        assert env_dec.sustain_decrease

    def test_ad_sr_field_split(self):
        """Verify AD is low 16 bits, SR is high 16 bits."""
        decoder = AdsrDecoder()
        # ad=0x80FF (attack mode exp, AR=0, DR=15, SL=15)
        # sr=0x1FC2 (RR=2, SR=0x7F, sustain_dir=0)
        env = decoder.decode(0x1FC280FF)

        assert env.sustain_level == 1.0  # SL=15 -> (15+1)/16 = 1.0
