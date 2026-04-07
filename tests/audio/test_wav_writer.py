# coding: utf-8

from struct import unpack_from

from howl_editor.audio.wav_writer import WavWriter


class TestWavWriter:

    def test_riff_header(self):
        writer = WavWriter()
        wav = writer.write(b"\x00\x00", 44100)

        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_mono_channels(self):
        writer = WavWriter()
        wav = writer.write(b"\x00\x00", 44100, channels=1)
        channels = unpack_from("<H", wav, 22)[0]

        assert channels == 1

    def test_stereo_channels(self):
        writer = WavWriter()
        wav = writer.write(b"\x00\x00\x00\x00", 44100, channels=2)
        channels = unpack_from("<H", wav, 22)[0]

        assert channels == 2

    def test_sample_rate(self):
        writer = WavWriter()
        wav = writer.write(b"", 22050)
        rate = unpack_from("<I", wav, 24)[0]

        assert rate == 22050

    def test_data_size(self):
        writer = WavWriter()
        pcm = b"\x01\x02\x03\x04"
        wav = writer.write(pcm, 44100)
        data_size = unpack_from("<I", wav, 40)[0]

        assert data_size == len(pcm)

    def test_total_size(self):
        writer = WavWriter()
        pcm = b"\x00" * 100
        wav = writer.write(pcm, 44100)

        assert len(wav) == 44 + len(pcm)

    def test_pcm_data_preserved(self):
        writer = WavWriter()
        pcm = b"\xAA\xBB\xCC\xDD"
        wav = writer.write(pcm, 44100)

        assert wav[44:] == pcm

    def test_empty_pcm(self):
        writer = WavWriter()
        wav = writer.write(b"", 44100)
        assert len(wav) == 44

        data_size = unpack_from("<I", wav, 40)[0]
        assert data_size == 0
