# coding: utf-8

from PySide6.QtWidgets import QSpinBox

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.voice.pitch_stepper import PitchStepper, SEMITONES_PER_OCTAVE

# Qt turns Page Up / Page Down into a step of ±10 rather than ±1.
_PAGE_STEP = 10

TOOLTIP = (
    "The SPU pitch register: 4096 plays the sample at 1.0× speed.\n"
    "The arrows step one semitone; Page Up / Page Down step a whole octave.\n"
    "Type a number for an exact register value."
)


class PitchSpinBox(QSpinBox):
    """A pitch register field whose arrows step a semitone and whose paging
    steps an octave — one raw count is a fraction of a cent, so stepping the
    number itself is useless for tuning."""

    def __init__(self, parent=None, pitch_stepper: PitchStepper | None = None):
        super().__init__(parent)
        self._stepper = pitch_stepper or PitchStepper()
        self.setRange(0, cseq_fmt.MAX_PITCH_REGISTER)
        self.setToolTip(TOOLTIP)

    def stepBy(self, steps: int) -> None:
        self.setValue(self._stepper.semitones(self.value(), self._semitones_for(steps)))

    def shift_octaves(self, octaves: int) -> None:
        self.setValue(self._stepper.octaves(self.value(), octaves))

    def _semitones_for(self, steps: int) -> int:
        if abs(steps) == _PAGE_STEP:
            return SEMITONES_PER_OCTAVE * (1 if steps > 0 else -1)

        return steps
