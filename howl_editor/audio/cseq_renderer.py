# coding: utf-8

from struct import pack

from howl_editor.audio.vag_decoder import VagDecoder
from howl_editor.models import CseqFile, CseqSong, CseqEventType


class _Voice:
    __slots__ = ("samples", "pos", "pitch_ratio")

    def __init__(self, samples: list[int], pitch_ratio: float):
        self.samples = samples
        self.pos: float = 0.0
        self.pitch_ratio = pitch_ratio

    def is_done(self) -> bool:
        return self.pos >= len(self.samples)

    def read(self) -> int:
        idx = int(self.pos)
        if idx >= len(self.samples):
            return 0

        sample = self.samples[idx]
        self.pos += self.pitch_ratio
        return sample


class CseqRenderer:

    def __init__(self, vag_decoder: VagDecoder):
        self._decoder = vag_decoder

    def render_song(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render a CSEQ song to 16-bit mono PCM bytes."""
        if song_index >= len(cseq.songs):
            return b""

        song = cseq.songs[song_index]
        decoded_cache: dict[int, list[int]] = {}
        samples = self._mix_song(song, cseq, sample_data, decoded_cache, output_rate)
        return b"".join(pack("<h", s) for s in samples)

    def render_song_to_wav(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render a CSEQ song to a complete WAV file."""
        pcm = self.render_song(cseq, song_index, sample_data, output_rate)
        return self._wrap_wav(pcm, output_rate)

    def _mix_song(
        self,
        song: CseqSong,
        cseq: CseqFile,
        sample_data: dict[int, bytes],
        decoded_cache: dict[int, list[int]],
        output_rate: int,
    ) -> list[int]:
        ticks_per_second = (song.bpm * song.tpqn) / 60.0
        if ticks_per_second <= 0:
            return []

        samples_per_tick = output_rate / ticks_per_second
        voices: list[_Voice] = []
        output: list[int] = []

        for track in song.tracks:
            patch_idx = 0
            tick = 0

            for event in track.events:
                tick += event.delta

                if event.event_type == CseqEventType.CHANGE_PATCH:
                    patch_idx = event.pitch

                elif event.event_type == CseqEventType.NOTE_ON:
                    voice = self._create_voice(
                        cseq, track.is_drum, patch_idx, event.pitch,
                        sample_data, decoded_cache, output_rate,
                    )

                    if voice:
                        start_sample = int(tick * samples_per_tick)
                        self._mix_voice_into(output, voice, start_sample, event.velocity)

                elif event.event_type in (
                    CseqEventType.END_TRACK,
                    CseqEventType.END_TRACK_2,
                    CseqEventType.TERMINATOR,
                ):
                    break

        return output

    def _create_voice(
        self,
        cseq: CseqFile,
        is_drum: bool,
        patch_idx: int,
        note_pitch: int,
        sample_data: dict[int, bytes],
        decoded_cache: dict[int, list[int]],
        output_rate: int,
    ) -> _Voice | None:
        if is_drum:
            if patch_idx >= len(cseq.percussions):
                return None

            inst = cseq.percussions[patch_idx]
            spu_id = inst.sample_id
            base_freq = inst.frequency
            pitch_ratio = (base_freq / 4096.0) * (44100.0 / output_rate)
        else:
            if patch_idx >= len(cseq.instruments):
                return None

            inst = cseq.instruments[patch_idx]
            spu_id = inst.sample_id
            base_freq = inst.frequency
            # Apply note pitch: semitone ratio relative to middle C (60)
            semitone_offset = note_pitch - 60
            freq_mult = 2.0 ** (semitone_offset / 12.0)
            pitch_ratio = (base_freq / 4096.0) * freq_mult * (44100.0 / output_rate)

        if spu_id not in sample_data:
            return None

        if spu_id not in decoded_cache:
            decoded_cache[spu_id] = self._decode_to_samples(sample_data[spu_id])

        return _Voice(decoded_cache[spu_id], pitch_ratio)

    def _decode_to_samples(self, raw: bytes) -> list[int]:
        pcm = self._decoder.decode(raw)
        return [int.from_bytes(pcm[i:i + 2], "little", signed=True) for i in range(0, len(pcm), 2)]

    def _mix_voice_into(
        self, output: list[int], voice: _Voice, start: int, velocity: int,
    ) -> None:
        vol = velocity / 255.0
        pos = start

        while not voice.is_done():
            sample = int(voice.read() * vol)

            if pos >= len(output):
                output.extend(0 for _ in range(pos - len(output) + 1))

            mixed = output[pos] + sample
            output[pos] = max(-32768, min(32767, mixed))
            pos += 1

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
