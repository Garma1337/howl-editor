# coding: utf-8

from struct import unpack_from

import pytest

from howl_editor.ps1.formats.vag.decoder import VagDecoder
from howl_editor.audio.wav_writer import WavWriter


@pytest.fixture
def decoder():
    return VagDecoder(WavWriter())


class TestDecode:

    def test_silent_frame(self, decoder):
        # predict=0, shift=0, flags=0, 14 zero data bytes
        frame = b"\x00\x00" + b"\x00" * 14
        pcm = decoder.decode(frame)

        # 28 samples, each 2 bytes
        assert len(pcm) == 28 * 2
        # All silence
        assert pcm == b"\x00\x00" * 28

    def test_end_flag_stops_decoding(self, decoder):
        frame1 = b"\x00\x00" + b"\x00" * 14
        frame2 = b"\x00\x07" + b"\x00" * 14  # flag=7 = end
        frame3 = b"\x00\x00" + b"\xFF" * 14  # should not be decoded
        pcm = decoder.decode(frame1 + frame2 + frame3)

        assert len(pcm) == 28 * 2 * 2  # only 2 frames

    def test_produces_nonzero_samples(self, decoder):
        # Non-zero data with shift=0 predict=1
        frame = b"\x10\x00" + bytes(range(14))
        pcm = decoder.decode(frame)
        assert len(pcm) == 28 * 2

        # At least some samples should be non-zero
        samples = [int.from_bytes(pcm[i:i + 2], "little", signed=True) for i in range(0, len(pcm), 2)]
        assert any(s != 0 for s in samples)

    def test_empty_data(self, decoder):
        pcm = decoder.decode(b"")
        assert pcm == b""

    def test_partial_frame_ignored(self, decoder):
        pcm = decoder.decode(b"\x00" * 10)  # less than 16 bytes
        assert pcm == b""


class TestDecodeToWav:

    def test_wav_header(self, decoder):
        frame = b"\x00\x07" + b"\x00" * 14  # single end frame
        wav = decoder.decode_to_wav(frame, sample_rate=11025)

        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "

    def test_wav_sample_rate(self, decoder):
        frame = b"\x00\x07" + b"\x00" * 14
        wav = decoder.decode_to_wav(frame, sample_rate=22050)
        rate = unpack_from("<I", wav, 24)[0]

        assert rate == 22050

    def test_wav_data_size(self, decoder):
        frame = b"\x00\x07" + b"\x00" * 14
        wav = decoder.decode_to_wav(frame, sample_rate=11025)
        data_size = unpack_from("<I", wav, 40)[0]

        assert data_size == 28 * 2  # 28 samples * 2 bytes
        assert len(wav) == 44 + data_size  # 44-byte header + data
