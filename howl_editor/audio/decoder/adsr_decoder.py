# coding: utf-8

from dataclasses import dataclass

from howl_editor.audio.settings.ps1 import PS1_SAMPLE_RATE

_MAX_ENVELOPE = 0x7FFF

_MIN_ATTACK_TIME = 0.001
_MIN_DECAY_TIME = 0.001
_MIN_RELEASE_TIME = 0.005
_MAX_PHASE_TIME = 5.0

_MAX_ATTACK_SHIFT = 31
_MAX_DECAY_SHIFT = 15
_MAX_RELEASE_SHIFT = 31

_SUSTAIN_LEVEL_STEPS = 16


@dataclass
class AdsrEnvelope:
    """Decoded ADSR envelope parameters."""
    attack_time: float = 0.001
    decay_time: float = 0.001
    sustain_level: float = 1.0
    release_time: float = 0.005
    sustain_decrease: bool = False
    sustain_shift: int = 0


class AdsrDecoder:
    """Decodes PS1 SPU ADSR register pairs into envelope parameters.

    The 32-bit ADSR value maps to two 16-bit SPU registers:
      low  16 bits = ADSR1 (attack mode, attack shift/step, decay shift, sustain level)
      high 16 bits = ADSR2 (sustain mode, sustain shift/step, release mode, release shift)
    """

    def decode(self, raw: int) -> AdsrEnvelope:
        adsr1 = raw & 0xFFFF
        adsr2 = (raw >> 16) & 0xFFFF

        sustain_level_raw = (adsr1 >> 0) & 0xF
        decay_shift = (adsr1 >> 4) & 0xF
        attack_step = (adsr1 >> 8) & 0x3
        attack_shift = (adsr1 >> 10) & 0x1F

        release_shift = (adsr2 >> 0) & 0x1F
        sustain_shift = (adsr2 >> 8) & 0x1F
        sustain_dir = (adsr2 >> 14) & 0x1

        sustain_level = self._decode_sustain_level(sustain_level_raw)

        return AdsrEnvelope(
            attack_time=self._compute_attack_time(attack_shift, attack_step),
            decay_time=self._compute_decay_time(decay_shift, sustain_level),
            sustain_level=sustain_level,
            release_time=self._compute_release_time(release_shift),
            sustain_decrease=(sustain_dir == 1),
            sustain_shift=sustain_shift,
        )

    def _decode_sustain_level(self, raw: int) -> float:
        return (raw + 1) / _SUSTAIN_LEVEL_STEPS

    def _compute_attack_time(self, shift: int, step: int) -> float:
        if shift >= _MAX_ATTACK_SHIFT:
            return _MIN_ATTACK_TIME

        cycles_per_step = (7 - step) << max(0, 11 - shift)
        steps_to_peak = _MAX_ENVELOPE // max(1, cycles_per_step)
        time = max(steps_to_peak, 1) / PS1_SAMPLE_RATE
        return self._clamp_time(time, _MIN_ATTACK_TIME)

    def _compute_decay_time(self, shift: int, sustain_level: float) -> float:
        if shift >= _MAX_DECAY_SHIFT:
            return _MIN_DECAY_TIME

        level_drop = max(0.01, 1.0 - sustain_level)
        time = (1 << shift) * level_drop / PS1_SAMPLE_RATE
        return self._clamp_time(time, _MIN_DECAY_TIME)

    def _compute_release_time(self, shift: int) -> float:
        if shift >= _MAX_RELEASE_SHIFT:
            return _MIN_RELEASE_TIME

        time = (1 << shift) * 4.0 / PS1_SAMPLE_RATE
        return self._clamp_time(time, _MIN_RELEASE_TIME)

    def _clamp_time(self, time: float, minimum: float) -> float:
        return min(max(time, minimum), _MAX_PHASE_TIME)
