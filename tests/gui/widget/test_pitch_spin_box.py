# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.gui.widget.pitch_spin_box import PitchSpinBox

UNITY = 4096


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def box(qt_app):
    spin = PitchSpinBox()
    spin.setValue(UNITY)
    return spin


class TestStepping:

    def test_arrow_up_steps_a_semitone(self, box):
        box.stepBy(1)

        assert box.value() == round(UNITY * 2 ** (1 / 12))

    def test_arrow_down_steps_a_semitone(self, box):
        box.stepBy(-1)

        assert box.value() == round(UNITY / 2 ** (1 / 12))

    def test_page_up_steps_an_octave(self, box):
        box.stepBy(10)

        assert box.value() == 2 * UNITY

    def test_page_down_steps_an_octave(self, box):
        box.stepBy(-10)

        assert box.value() == UNITY // 2

    def test_octave_button_doubles(self, box):
        box.shift_octaves(1)

        assert box.value() == 2 * UNITY

    def test_stays_inside_the_on_disc_field(self, box):
        box.setValue(cseq_fmt.MAX_PITCH_REGISTER)
        box.shift_octaves(1)

        assert box.value() == cseq_fmt.MAX_PITCH_REGISTER
