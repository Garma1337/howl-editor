# coding: utf-8

from struct import pack

# PSX VAG ADPCM prediction filter coefficients (fixed-point, /64)
_COEFFICIENTS = [
    (0, 0),
    (60, 0),
    (115, -52),
    (98, -55),
    (122, -60),
]

_FRAME_SIZE = 16
_SAMPLES_PER_FRAME = 28
_FLAG_END = 7


class VagDecoder:

    def decode(self, data: bytes, sample_rate: int = 11025) -> bytes:
        """Decode raw VAG ADPCM data to 16-bit signed PCM bytes."""
        samples = self._decode_samples(data)
        return self._samples_to_bytes(samples)

    def decode_to_wav(self, data: bytes, sample_rate: int = 11025) -> bytes:
        """Decode raw VAG ADPCM data to a complete WAV file."""
        pcm = self.decode(data, sample_rate)
        return self._wrap_wav(pcm, sample_rate)

    def _decode_samples(self, data: bytes) -> list[int]:
        samples = []
        prev1 = 0
        prev2 = 0
        offset = 0

        while offset + _FRAME_SIZE <= len(data):
            predict_shift = data[offset]
            flags = data[offset + 1]

            predict_nr = (predict_shift >> 4) & 0xF
            shift_factor = predict_shift & 0xF

            if predict_nr >= len(_COEFFICIENTS):
                predict_nr = 0

            f0, f1 = _COEFFICIENTS[predict_nr]

            for i in range(2, _FRAME_SIZE):
                byte = data[offset + i]

                for nibble in (byte & 0xF, (byte >> 4) & 0xF):
                    signed = nibble - 16 if nibble >= 8 else nibble
                    sample = signed << (12 - shift_factor)
                    sample += (prev1 * f0 + prev2 * f1 + 32) >> 6
                    sample = max(-32768, min(32767, sample))
                    samples.append(sample)
                    prev2 = prev1
                    prev1 = sample

            if flags == _FLAG_END:
                break

            offset += _FRAME_SIZE

        return samples

    def _samples_to_bytes(self, samples: list[int]) -> bytes:
        return b"".join(pack("<h", s) for s in samples)

    def _wrap_wav(self, pcm: bytes, sample_rate: int) -> bytes:
        channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm)
        file_size = 36 + data_size

        header = pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", file_size, b"WAVE",
            b"fmt ", 16, 1, channels,
            sample_rate, byte_rate, block_align, bits_per_sample,
            b"data", data_size,
        )

        return header + pcm
