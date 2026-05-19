# coding: utf-8

from struct import pack, unpack


class LinearInterpolationResampler:
    """Linear-interpolation resampler for 16-bit signed mono PCM.

    Used to bump audibly-correct low-rate samples up to a rate the playback
    backend will actually emit."""

    def resample(self, pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
        if src_rate == dst_rate or src_rate <= 0 or dst_rate <= 0 or not pcm:
            return pcm

        samples = unpack(f"<{len(pcm) // 2}h", pcm)
        in_count = len(samples)
        out_count = max(1, round(in_count * dst_rate / src_rate))
        ratio = src_rate / dst_rate

        out: list[int] = []

        for i in range(out_count):
            pos = i * ratio
            idx = int(pos)

            if idx + 1 < in_count:
                frac = pos - idx
                out.append(int(samples[idx] + (samples[idx + 1] - samples[idx]) * frac))
            elif idx < in_count:
                out.append(samples[idx])
            else:
                break

        return pack(f"<{len(out)}h", *out)
