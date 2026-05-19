# coding: utf-8

from howl_editor.audio.vag_sample_rate_provider import VagSampleRateProvider


class TestVagSampleRateProvider:

    def test_default_is_11025(self):
        provider = VagSampleRateProvider()
        assert provider.rate == 11025

    def test_constructor_accepts_preset(self):
        provider = VagSampleRateProvider(default=44100)
        assert provider.rate == 44100

    def test_constructor_falls_back_when_non_preset(self):
        provider = VagSampleRateProvider(default=12345)
        assert provider.rate == 11025

    def test_set_accepts_preset(self):
        provider = VagSampleRateProvider()
        provider.set(22050)
        assert provider.rate == 22050

    def test_set_ignores_non_preset(self):
        provider = VagSampleRateProvider()
        provider.set(99999)
        assert provider.rate == 11025

    def test_presets_are_immutable_tuple(self):
        # PRESETS is consumed by the Tools menu builder; making sure no one
        # ever .appends to it accidentally.
        assert isinstance(VagSampleRateProvider.PRESETS, tuple)
        assert 11025 in VagSampleRateProvider.PRESETS
        assert 44100 in VagSampleRateProvider.PRESETS
