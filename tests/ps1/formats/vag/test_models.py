# coding: utf-8

from howl_editor.ps1.formats.vag.models import VagSample


class TestVagSample:

    def test_defaults(self):
        s = VagSample()

        assert s.sample_rate == 44100
        assert s.data == b""

    def test_with_data(self):
        s = VagSample(data=b"\x01\x02\x03")

        assert len(s.data) == 3
