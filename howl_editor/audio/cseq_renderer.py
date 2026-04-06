# coding: utf-8

from struct import pack

from howl_editor.audio.decoder.adsr_decoder import AdsrDecoder, AdsrEnvelope
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.ps1 import PS1_SAMPLE_RATE, PS1_FREQUENCY_UNIT
from howl_editor.audio.voice import Voice
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.models import CseqFile, CseqSong, CseqEventType

_PERCUSSION_ENVELOPE = AdsrEnvelope(
    attack_time=0.001,
    decay_time=0.0,
    sustain_level=1.0,
    release_time=0.005,
    sustain_decrease=False,
    sustain_shift=31,
)

_PERCUSSION_VOLUME_SCALE = 0.40
_MIDDLE_C = 60
_MAX_VOLUME = 255.0
_MAX_PAN = 127.0
_SAMPLE_CLAMP_MIN = -32768
_SAMPLE_CLAMP_MAX = 32767
_TAIL_SECONDS = 5


class CseqRenderer:

    def __init__(self, vag_decoder: VagDecoder, adsr_decoder: AdsrDecoder, wav_writer: WavWriter):
        self._decoder = vag_decoder
        self._adsr = adsr_decoder
        self._wav_writer = wav_writer

    def render_song(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render a CSEQ song to 16-bit stereo PCM bytes."""
        if song_index >= len(cseq.songs):
            return b""

        song = cseq.songs[song_index]
        decoded_cache: dict[int, tuple[list[int], int]] = {}
        left, right = self._mix_song(song, cseq, sample_data, decoded_cache, output_rate)
        return self._interleave_stereo(left, right)

    def render_song_to_wav(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render a CSEQ song to a complete WAV file."""
        pcm = self.render_song(cseq, song_index, sample_data, output_rate)
        return self._wav_writer.write(pcm, output_rate, channels=2)

    def _interleave_stereo(self, left: list[int], right: list[int]) -> bytes:
        out = bytearray(len(left) * 4)

        for i in range(len(left)):
            out[i * 4:i * 4 + 4] = pack("<hh", left[i], right[i])

        return bytes(out)

    def _mix_song(
        self,
        song: CseqSong,
        cseq: CseqFile,
        sample_data: dict[int, bytes],
        decoded_cache: dict[int, tuple[list[int], int]],
        output_rate: int,
    ) -> tuple[list[int], list[int]]:
        ticks_per_second = self._compute_ticks_per_second(song.bpm, song.tpqn)
        if ticks_per_second <= 0:
            return [], []

        samples_per_tick = output_rate / ticks_per_second
        dt = 1.0 / output_rate

        voice_events = self._collect_voice_events(
            song, cseq, sample_data, decoded_cache, output_rate, samples_per_tick,
        )

        if not voice_events:
            return [], []

        voice_events.sort(key=lambda x: x[0])

        return self._render_voices(voice_events, output_rate, dt)

    def _compute_ticks_per_second(self, bpm: int, tpqn: int) -> float:
        return (bpm * tpqn) / 60.0

    def _tick_to_sample(self, tick: int, samples_per_tick: float) -> int:
        return int(tick * samples_per_tick)

    def _collect_voice_events(
        self,
        song: CseqSong,
        cseq: CseqFile,
        sample_data: dict[int, bytes],
        decoded_cache: dict[int, tuple[list[int], int]],
        output_rate: int,
        samples_per_tick: float,
    ) -> list[tuple[int, str, Voice]]:
        events: list[tuple[int, str, Voice]] = []

        for track in song.tracks:
            patch_idx = 0
            cur_velocity = 127
            cur_pan = 64
            tick = 0
            active_notes: dict[int, list[Voice]] = {}

            for event in track.events:
                tick += event.delta

                if event.event_type == CseqEventType.CHANGE_PATCH:
                    patch_idx = event.pitch
                elif event.event_type == CseqEventType.VELOCITY:
                    cur_velocity = event.pitch
                elif event.event_type == CseqEventType.PAN:
                    cur_pan = event.pitch
                elif event.event_type == CseqEventType.NOTE_ON:
                    start = self._tick_to_sample(tick, samples_per_tick)
                    vel = event.velocity if event.velocity > 0 else cur_velocity
                    voice = self._create_voice(
                        cseq, track.is_drum, patch_idx, event.pitch,
                        vel, cur_pan, sample_data, decoded_cache, output_rate,
                    )

                    if voice:
                        events.append((start, "on", voice))
                        active_notes.setdefault(event.pitch, []).append(voice)
                elif event.event_type == CseqEventType.NOTE_OFF:
                    off = self._tick_to_sample(tick, samples_per_tick)

                    if event.pitch in active_notes and active_notes[event.pitch]:
                        voice = active_notes[event.pitch].pop(0)
                        events.append((off, "off", voice))
                elif event.event_type in (
                    CseqEventType.END_TRACK,
                    CseqEventType.END_TRACK_2,
                    CseqEventType.TERMINATOR,
                ):
                    off = self._tick_to_sample(tick, samples_per_tick)
                    for note_voices in active_notes.values():
                        for v in note_voices:
                            events.append((off, "off", v))

                    active_notes.clear()
                    break

        return events

    def _render_voices(
        self,
        voice_events: list[tuple[int, str, Voice]],
        output_rate: int,
        dt: float,
    ) -> tuple[list[int], list[int]]:
        output_left: list[int] = []
        output_right: list[int] = []
        active_voices: list[Voice] = []
        event_idx = 0
        sample_pos = 0

        max_start = max((e[0] for e in voice_events), default=0)
        total_estimate = max_start + output_rate * _TAIL_SECONDS

        while sample_pos < total_estimate or active_voices:
            while event_idx < len(voice_events) and voice_events[event_idx][0] <= sample_pos:
                _, action, voice = voice_events[event_idx]

                if action == "on":
                    active_voices.append(voice)
                else:
                    voice.note_off()

                event_idx += 1

            mix_l, mix_r = self._mix_active_voices(active_voices, dt)
            active_voices = [v for v in active_voices if not v.is_done()]

            output_left.append(self._clamp_sample(mix_l))
            output_right.append(self._clamp_sample(mix_r))
            sample_pos += 1

            if event_idx >= len(voice_events) and not active_voices:
                break

        return output_left, output_right

    def _mix_active_voices(self, voices: list[Voice], dt: float) -> tuple[float, float]:
        mix_l = 0.0
        mix_r = 0.0

        for voice in voices:
            if voice.is_done():
                continue

            env = voice.advance_envelope(dt)
            raw = voice.read()
            amplitude = raw * env * voice.volume * voice.velocity
            pan_l, pan_r = self._compute_pan(voice.pan)
            mix_l += amplitude * pan_l
            mix_r += amplitude * pan_r

        return mix_l, mix_r

    def _compute_pan(self, pan: float) -> tuple[float, float]:
        pan_r = pan / _MAX_PAN
        pan_l = 1.0 - pan_r
        return pan_l, pan_r

    def _clamp_sample(self, value: float) -> int:
        return max(_SAMPLE_CLAMP_MIN, min(_SAMPLE_CLAMP_MAX, int(value)))

    def _create_voice(
        self,
        cseq: CseqFile,
        is_drum: bool,
        patch_idx: int,
        note_pitch: int,
        velocity: int,
        pan: int,
        sample_data: dict[int, bytes],
        decoded_cache: dict[int, tuple[list[int], int]],
        output_rate: int,
    ) -> Voice | None:
        if is_drum:
            if patch_idx >= len(cseq.percussions):
                return None

            inst = cseq.percussions[patch_idx]
            pitch_ratio = self._compute_drum_pitch(inst.frequency, output_rate)
            inst_volume = self._normalize_volume(inst.volume) * _PERCUSSION_VOLUME_SCALE
            envelope = _PERCUSSION_ENVELOPE
        else:
            if patch_idx >= len(cseq.instruments):
                return None

            inst = cseq.instruments[patch_idx]
            pitch_ratio = self._compute_melodic_pitch(inst.frequency, note_pitch, output_rate)
            inst_volume = self._normalize_volume(inst.volume)
            envelope = self._adsr.decode(inst.adsr)

        spu_id = inst.sample_id
        if spu_id not in sample_data:
            return None

        if spu_id not in decoded_cache:
            decoded_cache[spu_id] = self._decoder.decode_with_loop(sample_data[spu_id])

        samples, loop_start = decoded_cache[spu_id]

        return Voice(
            samples=samples,
            loop_start=loop_start,
            pitch_ratio=pitch_ratio,
            volume=inst_volume,
            pan=float(pan),
            velocity=self._normalize_volume(velocity),
            envelope=envelope,
        )

    def _compute_drum_pitch(self, frequency: int, output_rate: int) -> float:
        return (frequency / PS1_FREQUENCY_UNIT) * (PS1_SAMPLE_RATE / output_rate)

    def _compute_melodic_pitch(self, frequency: int, note_pitch: int, output_rate: int) -> float:
        semitone_offset = note_pitch - _MIDDLE_C
        freq_mult = 2.0 ** (semitone_offset / 12.0)
        return (frequency / PS1_FREQUENCY_UNIT) * freq_mult * (PS1_SAMPLE_RATE / output_rate)

    def _normalize_volume(self, value: int) -> float:
        return value / _MAX_VOLUME
