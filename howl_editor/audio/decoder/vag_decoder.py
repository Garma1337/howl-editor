# coding: utf-8

from struct import pack

from howl_editor.audio.wav_writer import WavWriter

# PSX VAG ADPCM prediction filter coefficients (fixed-point, divided by 64)
_FILTER_COEFFICIENTS = [
    (0, 0),
    (60, 0),
    (115, -52),
    (98, -55),
    (122, -60),
]

_FRAME_SIZE = 16
_FRAME_HEADER_SIZE = 2
_NIBBLE_SIGN_THRESHOLD = 8
_NIBBLE_SIGN_OFFSET = 16
_ADPCM_FIXED_POINT_SHIFT = 12
_FILTER_ROUNDING = 32
_FILTER_SHIFT = 6

_SAMPLE_MIN = -32768
_SAMPLE_MAX = 32767

_FLAG_LOOP_END = 1
_FLAG_LOOP_REPEAT = 2
_FLAG_LOOP_START = 4
_FLAG_END_OF_DATA = 7


class VagDecoder:

    def __init__(self, wav_writer: WavWriter):
        self._wav_writer = wav_writer

    def decode(self, data: bytes) -> bytes:
        """Decode raw VAG ADPCM data to 16-bit signed PCM bytes."""
        samples, _ = self._decode_samples(data)
        return self._samples_to_bytes(samples)

    def decode_with_loop(self, data: bytes) -> tuple[list[int], int]:
        """Decode VAG data returning (samples, loop_start_sample_index).

        loop_start_sample_index is -1 if no loop point is found.
        """
        return self._decode_samples(data)

    def decode_to_wav(self, data: bytes, sample_rate: int = 11025) -> bytes:
        """Decode raw VAG ADPCM data to a complete WAV file."""
        pcm = self.decode(data)
        return self._wav_writer.write(pcm, sample_rate, channels=1)

    def _decode_samples(self, data: bytes) -> tuple[list[int], int]:
        samples: list[int] = []
        prev1 = 0
        prev2 = 0
        offset = 0
        loop_start = -1

        while offset + _FRAME_SIZE <= len(data):
            predict_nr, shift_factor = self._parse_frame_header(data[offset])
            flags = data[offset + 1]

            if flags & _FLAG_LOOP_START:
                loop_start = len(samples)

            prev1, prev2 = self._decode_frame(
                data, offset, predict_nr, shift_factor, prev1, prev2, samples,
            )

            if self._is_end_frame(flags):
                break

            offset += _FRAME_SIZE

        return samples, loop_start

    def _parse_frame_header(self, byte: int) -> tuple[int, int]:
        predict_nr = (byte >> 4) & 0xF

        if predict_nr >= len(_FILTER_COEFFICIENTS):
            predict_nr = 0

        shift_factor = byte & 0xF
        return predict_nr, shift_factor

    def _decode_frame(
        self,
        data: bytes,
        offset: int,
        predict_nr: int,
        shift_factor: int,
        prev1: int,
        prev2: int,
        samples: list[int],
    ) -> tuple[int, int]:
        f0, f1 = _FILTER_COEFFICIENTS[predict_nr]

        for i in range(_FRAME_HEADER_SIZE, _FRAME_SIZE):
            byte = data[offset + i]

            for nibble in self._extract_nibbles(byte):
                signed = self._sign_extend_nibble(nibble)
                sample = self._compute_sample(signed, shift_factor, prev1, prev2, f0, f1)
                samples.append(sample)
                prev2 = prev1
                prev1 = sample

        return prev1, prev2

    def _extract_nibbles(self, byte: int) -> tuple[int, int]:
        return byte & 0xF, (byte >> 4) & 0xF

    def _sign_extend_nibble(self, nibble: int) -> int:
        if nibble >= _NIBBLE_SIGN_THRESHOLD:
            return nibble - _NIBBLE_SIGN_OFFSET

        return nibble

    def _compute_sample(
        self, signed: int, shift: int, prev1: int, prev2: int, f0: int, f1: int,
    ) -> int:
        sample = signed << (_ADPCM_FIXED_POINT_SHIFT - shift)
        sample += (prev1 * f0 + prev2 * f1 + _FILTER_ROUNDING) >> _FILTER_SHIFT
        return max(_SAMPLE_MIN, min(_SAMPLE_MAX, sample))

    def _is_end_frame(self, flags: int) -> bool:
        if flags == _FLAG_END_OF_DATA:
            return True

        return bool((flags & _FLAG_LOOP_END) and (flags & _FLAG_LOOP_REPEAT))

    def _samples_to_bytes(self, samples: list[int]) -> bytes:
        return b"".join(pack("<h", s) for s in samples)
