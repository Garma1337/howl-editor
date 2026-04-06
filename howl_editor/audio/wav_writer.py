# coding: utf-8

from struct import pack

_BITS_PER_SAMPLE = 16
_FORMAT_PCM = 1
_FMT_CHUNK_SIZE = 16
_HEADER_SIZE = 36


class WavWriter:
    """Wraps raw PCM data into a WAV file."""

    def write(self, pcm: bytes, sample_rate: int, channels: int = 1) -> bytes:
        byte_rate = sample_rate * channels * _BITS_PER_SAMPLE // 8
        block_align = channels * _BITS_PER_SAMPLE // 8
        data_size = len(pcm)

        header = pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", _HEADER_SIZE + data_size, b"WAVE",
            b"fmt ", _FMT_CHUNK_SIZE, _FORMAT_PCM, channels,
            sample_rate, byte_rate, block_align, _BITS_PER_SAMPLE,
            b"data", data_size,
        )

        return header + pcm
