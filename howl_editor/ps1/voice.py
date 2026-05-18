# coding: utf-8

from howl_editor.ps1 import spu
from howl_editor.ps1.adsr_decoder import AdsrEnvelope


_SUSTAIN_DECAY_FACTOR = 0.0001


class Voice:
    """A single playing voice with sample playback, looping, and ADSR envelope.

    Holds immutable note metadata (inst_vol, note_vel, base_pitch, note_index,
    is_drum, output_rate) so that callers can recalculate gain or pitch for
    mid-note updates without needing a side-channel lookup.
    """

    PHASE_ATTACK = 0
    PHASE_DECAY = 1
    PHASE_SUSTAIN = 2
    PHASE_RELEASE = 3

    def __init__(
        self,
        samples: list[int],
        loop_start: int,
        pitch_ratio: float,
        gain_l: float,
        gain_r: float,
        envelope: AdsrEnvelope,
        inst_vol: int = 0,
        note_vel: int = 0,
        base_pitch: int = 0,
        note_index: int = 0,
        is_drum: bool = False,
        output_rate: int = 22050,
    ):
        self.samples = samples
        self.loop_start = loop_start
        self.pos: float = 0.0
        self.pitch_ratio = pitch_ratio
        self.gain_l = gain_l
        self.gain_r = gain_r
        self.envelope = envelope

        # Immutable note metadata — kept for mid-note recalculation
        self.inst_vol = inst_vol
        self.note_vel = note_vel
        self.base_pitch = base_pitch
        self.note_index = note_index
        self.is_drum = is_drum
        self.output_rate = output_rate

        self.env_phase = self.PHASE_ATTACK
        self.env_level = 0.0
        self.active = True

    def note_off(self) -> None:
        self.env_phase = self.PHASE_RELEASE

    def is_done(self) -> bool:
        return not self.active

    def advance_envelope(self, dt: float) -> float:
        e = self.envelope

        if self.env_phase == self.PHASE_ATTACK:
            self.env_level = self._advance_attack(dt, e)
        elif self.env_phase == self.PHASE_DECAY:
            self.env_level = self._advance_decay(dt, e)
        elif self.env_phase == self.PHASE_SUSTAIN:
            self.env_level = self._advance_sustain(dt, e)
        elif self.env_phase == self.PHASE_RELEASE:
            self.env_level = self._advance_release(dt, e)

        return max(0.0, min(1.0, self.env_level))

    def _advance_attack(self, dt: float, e: AdsrEnvelope) -> float:
        level = self.env_level

        if e.attack_time > 0:
            level += dt / e.attack_time
        else:
            level = 1.0

        if level >= 1.0:
            level = 1.0
            self.env_phase = self.PHASE_DECAY

        return level

    def _advance_decay(self, dt: float, e: AdsrEnvelope) -> float:
        level = self.env_level

        if e.decay_time > 0:
            decay_amount = dt / e.decay_time * (1.0 - e.sustain_level)
            level -= decay_amount

        if level <= e.sustain_level:
            level = e.sustain_level
            self.env_phase = self.PHASE_SUSTAIN

        return level

    def _advance_sustain(self, dt: float, e: AdsrEnvelope) -> float:
        level = self.env_level

        if e.sustain_decrease and e.sustain_shift < spu.MAX_SUSTAIN_SHIFT:
            rate = self._compute_sustain_decay_rate(e.sustain_shift)
            level -= dt * rate

            if level < 0:
                level = 0

        return level

    def _compute_sustain_decay_rate(self, shift: int) -> float:
        shift_duration = (1 << shift) / spu.SAMPLE_RATE
        return _SUSTAIN_DECAY_FACTOR / max(0.1, shift_duration)

    def _advance_release(self, dt: float, e: AdsrEnvelope) -> float:
        level = self.env_level

        if e.release_time > 0:
            level -= dt / e.release_time
        else:
            level = 0.0

        if level <= 0:
            level = 0.0
            self.active = False

        return level

    def read(self) -> int:
        if not self.active:
            return 0

        idx = int(self.pos)

        if idx >= len(self.samples):
            if not self._try_loop():
                return 0

            idx = int(self.pos)

        next_idx = self._next_sample_index(idx)
        sample = self._interpolate(idx, next_idx)
        self.pos += self.pitch_ratio

        return int(sample)

    def _try_loop(self) -> bool:
        if self.loop_start < 0:
            self.active = False
            return False

        loop_len = len(self.samples) - self.loop_start
        if loop_len <= 0:
            self.active = False
            return False

        self.pos = self.loop_start + (self.pos - len(self.samples)) % loop_len
        return True

    def _next_sample_index(self, idx: int) -> int:
        next_idx = idx + 1

        if next_idx >= len(self.samples):
            if 0 <= self.loop_start < len(self.samples):
                return self.loop_start

            return idx

        return next_idx

    def _interpolate(self, idx: int, next_idx: int) -> float:
        frac = self.pos - idx
        return self.samples[idx] * (1.0 - frac) + self.samples[next_idx] * frac
