# coding: utf-8

from array import array
from struct import pack

from howl_editor.audio.decoder.adsr_decoder import AdsrDecoder, AdsrEnvelope
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.settings.ctr import DEFAULT_DISTORT, DEFAULT_PAN, DEFAULT_SEQ_VOL
from howl_editor.audio.voice import Voice, PitchCalculator, GainCalculator
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.models import CseqFile, CseqSong, CseqEventType

# CTR default percussion ADSR: ad=0x80FF, sr=0x1FC2
_PERCUSSION_ENVELOPE = AdsrEnvelope(
    attack_time=0.001,
    decay_time=0.001,
    sustain_level=1.0,
    release_time=0.005,
    sustain_decrease=False,
    sustain_shift=31,
)

_SAMPLE_CLAMP_MIN = -32768
_SAMPLE_CLAMP_MAX = 32767
_TAIL_SECONDS = 5

# Voice event actions
_ON = "on"
_OFF = "off"
_UPDATE = "update"
_BEND = "bend"


class CseqRenderer:

    def __init__(
        self,
        vag_decoder: VagDecoder,
        adsr_decoder: AdsrDecoder,
        wav_writer: WavWriter,
        pitch_calculator: PitchCalculator,
        gain_calculator: GainCalculator,
    ):
        self._decoder = vag_decoder
        self._adsr = adsr_decoder
        self._wav_writer = wav_writer
        self._pitch = pitch_calculator
        self._gain = gain_calculator
        self._decode_cache: dict[bytes, tuple[list[int], int]] = {}

    def clear_decode_cache(self) -> None:
        """Drop the VAG-decoded sample cache. Called when the loaded HWL
        changes so stale sample bytes don't pin memory."""
        self._decode_cache.clear()

    def render_song(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
        active_tracks: list[int] | None = None,
    ) -> bytes:
        """Render a CSEQ song to 16-bit stereo PCM bytes."""
        if song_index >= len(cseq.songs):
            return b""

        song = cseq.songs[song_index]
        if active_tracks is not None:
            tracks = [song.tracks[i] for i in active_tracks if 0 <= i < len(song.tracks)]
            song = type(song)(
                unk0=song.unk0, bpm=song.bpm, tpqn=song.tpqn, tracks=tracks,
            )

        left, right = self._mix_song(song, cseq, sample_data, self._decode_cache, output_rate)
        return self._interleave_stereo(left, right)

    def render_song_to_wav(
        self,
        cseq: CseqFile,
        song_index: int,
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
        active_tracks: list[int] | None = None,
    ) -> bytes:
        """Render a CSEQ song to a complete WAV file."""
        pcm = self.render_song(cseq, song_index, sample_data, output_rate, active_tracks)
        return self._wav_writer.write(pcm, output_rate, channels=2)

    def render_layered(
        self,
        cseq: CseqFile,
        song_indices: list[int],
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render multiple CSEQ songs as if played simultaneously (mixed PCM).

        Used by the Adventure Hub preview: layered hub music plays several
        sequences in parallel at runtime, controlled by a per-sequence mask.
        Each sequence is rendered independently then summed sample-wise.
        """
        streams = [
            self.render_song(cseq, idx, sample_data, output_rate)
            for idx in song_indices
            if idx < len(cseq.songs)
        ]
        streams = [s for s in streams if s]

        if not streams:
            return b""

        if len(streams) == 1:
            return streams[0]

        return self._mix_pcm_streams(streams)

    def render_layered_to_wav(
        self,
        cseq: CseqFile,
        song_indices: list[int],
        sample_data: dict[int, bytes],
        output_rate: int = 22050,
    ) -> bytes:
        """Render a layered set of CSEQ sequences to a complete WAV file."""
        pcm = self.render_layered(cseq, song_indices, sample_data, output_rate)
        return self._wav_writer.write(pcm, output_rate, channels=2)

    def _mix_pcm_streams(self, streams: list[bytes]) -> bytes:
        """Sum int16 stereo PCM streams sample-wise, clamping to int16 range.

        Shorter streams are padded with silence so the result is the length of
        the longest input (so a long melodic layer isn't truncated by a short
        drum loop, for example).
        """
        max_byte_len = max(len(s) for s in streams)
        sample_count = max_byte_len // 2  # int16 samples (stereo interleaved)
        accumulator = [0] * sample_count

        for stream in streams:
            buf = array("h")
            buf.frombytes(stream)

            for i, value in enumerate(buf):
                accumulator[i] += value

        clamped = array("h", (
            max(_SAMPLE_CLAMP_MIN, min(_SAMPLE_CLAMP_MAX, v)) for v in accumulator
        ))

        return clamped.tobytes()

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
        decoded_cache: dict[bytes, tuple[list[int], int]],
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
        decoded_cache: dict[bytes, tuple[list[int], int]],
        output_rate: int,
        samples_per_tick: float,
    ) -> list[tuple]:
        events: list[tuple] = []

        for track in song.tracks:
            patch_idx = 0
            seq_vol = DEFAULT_SEQ_VOL
            cur_pan = DEFAULT_PAN
            distort = DEFAULT_DISTORT
            tick = 0
            active_notes: dict[int, list[Voice]] = {}
            live_voices: list[Voice] = []

            for event in track.events:
                tick += event.delta

                if event.event_type == CseqEventType.CHANGE_PATCH:
                    patch_idx = event.pitch

                elif event.event_type == CseqEventType.VELOCITY:
                    seq_vol = event.pitch
                    pos = self._tick_to_sample(tick, samples_per_tick)
                    if live_voices:
                        events.append((pos, _UPDATE, list(live_voices), (seq_vol, cur_pan)))

                elif event.event_type == CseqEventType.PAN:
                    cur_pan = event.pitch
                    pos = self._tick_to_sample(tick, samples_per_tick)
                    if live_voices:
                        events.append((pos, _UPDATE, list(live_voices), (seq_vol, cur_pan)))

                elif event.event_type == CseqEventType.PITCH_BEND:
                    distort = event.pitch
                    pos = self._tick_to_sample(tick, samples_per_tick)
                    if live_voices:
                        events.append((pos, _BEND, list(live_voices), distort))

                elif event.event_type == CseqEventType.NOTE_ON:
                    if event.velocity == 0:
                        continue

                    start = self._tick_to_sample(tick, samples_per_tick)
                    voice = self._create_voice(
                        cseq, track.is_drum, patch_idx, event.pitch,
                        event.velocity, seq_vol, cur_pan, distort,
                        sample_data, decoded_cache, output_rate,
                    )

                    if voice:
                        events.append((start, _ON, voice, None))
                        active_notes.setdefault(event.pitch, []).append(voice)
                        live_voices.append(voice)

                elif event.event_type == CseqEventType.NOTE_OFF:
                    off = self._tick_to_sample(tick, samples_per_tick)

                    if event.pitch in active_notes and active_notes[event.pitch]:
                        voice = active_notes[event.pitch].pop(0)
                        events.append((off, _OFF, voice, None))
                        if voice in live_voices:
                            live_voices.remove(voice)

                elif event.event_type in (
                    CseqEventType.END_TRACK,
                    CseqEventType.END_TRACK_2,
                    CseqEventType.TERMINATOR,
                ):
                    off = self._tick_to_sample(tick, samples_per_tick)
                    for note_voices in active_notes.values():
                        for v in note_voices:
                            events.append((off, _OFF, v, None))

                    active_notes.clear()
                    live_voices.clear()
                    break

        return events

    def _render_voices(
        self,
        voice_events: list[tuple],
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
                evt = voice_events[event_idx]
                action = evt[1]

                if action == _ON:
                    active_voices.append(evt[2])
                elif action == _OFF:
                    evt[2].note_off()
                elif action == _UPDATE:
                    new_seq_vol, new_pan = evt[3]
                    for v in evt[2]:
                        v.gain_l, v.gain_r = self._gain.compute(
                            v.inst_vol, v.note_vel, new_seq_vol, new_pan,
                        )
                elif action == _BEND:
                    new_distort = evt[3]
                    for v in evt[2]:
                        if v.is_drum:
                            v.pitch_ratio = self._pitch.drum(
                                v.base_pitch, new_distort, v.output_rate,
                            )
                        else:
                            v.pitch_ratio = self._pitch.instrument(
                                v.base_pitch, v.note_index, new_distort, v.output_rate,
                            )

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
            sample = raw * env
            mix_l += sample * voice.gain_l
            mix_r += sample * voice.gain_r

        return mix_l, mix_r

    def _clamp_sample(self, value: float) -> int:
        return max(_SAMPLE_CLAMP_MIN, min(_SAMPLE_CLAMP_MAX, int(value)))

    def _create_voice(
        self,
        cseq: CseqFile,
        is_drum: bool,
        patch_idx: int,
        note_pitch: int,
        note_vel: int,
        seq_vol: int,
        pan: int,
        distort: int,
        sample_data: dict[int, bytes],
        decoded_cache: dict[bytes, tuple[list[int], int]],
        output_rate: int,
    ) -> Voice | None:
        if is_drum:
            perc_idx = note_pitch
            if perc_idx >= len(cseq.percussions):
                return None

            inst = cseq.percussions[perc_idx]
            pitch_ratio = self._pitch.drum(inst.frequency, distort, output_rate)
            envelope = _PERCUSSION_ENVELOPE
            base_pitch = inst.frequency
            note_index = 0
        else:
            if patch_idx >= len(cseq.instruments):
                return None

            inst = cseq.instruments[patch_idx]
            pitch_ratio = self._pitch.instrument(inst.frequency, note_pitch, distort, output_rate)
            envelope = self._adsr.decode(inst.adsr)
            base_pitch = inst.frequency
            note_index = note_pitch

        spu_id = inst.sample_id
        if spu_id not in sample_data:
            return None

        sample_bytes = sample_data[spu_id]
        decoded = decoded_cache.get(sample_bytes)

        if decoded is None:
            decoded = self._decoder.decode_with_loop(sample_bytes)
            decoded_cache[sample_bytes] = decoded

        samples, loop_start = decoded
        gain_l, gain_r = self._gain.compute(inst.volume, note_vel, seq_vol, pan)

        return Voice(
            samples=samples,
            loop_start=loop_start,
            pitch_ratio=pitch_ratio,
            gain_l=gain_l,
            gain_r=gain_r,
            envelope=envelope,
            inst_vol=inst.volume,
            note_vel=note_vel,
            base_pitch=base_pitch,
            note_index=note_index,
            is_drum=is_drum,
            output_rate=output_rate,
        )
