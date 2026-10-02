# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.dialog.edit_instrument_dialog import EditInstrumentDialog
from howl_editor.ps1 import spu

UNITY = 4096


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _dialog(frequency: int = UNITY, adsr: int | None = None) -> EditInstrumentDialog:
    return EditInstrumentDialog(
        None, title="t", subject_label="s",
        initial_volume=255, initial_frequency=frequency, initial_adsr=adsr,
    )


class TestOctaveButtons:

    def test_octave_up_doubles_the_stored_pitch(self, qt_app):
        dlg = _dialog()

        dlg._frequency.shift_octaves(1)

        assert dlg.chosen().frequency == 2 * UNITY

    def test_octave_down_halves_the_stored_pitch(self, qt_app):
        dlg = _dialog()

        dlg._frequency.shift_octaves(-1)

        assert dlg.chosen().frequency == UNITY // 2

    def test_round_trip_returns_to_the_original(self, qt_app):
        dlg = _dialog(frequency=1234)

        dlg._frequency.shift_octaves(1)
        dlg._frequency.shift_octaves(-1)

        assert dlg.chosen().frequency == 1234


class TestCeilingWarning:

    def test_quiet_below_the_ceiling(self, qt_app):
        assert _dialog(frequency=spu.MAX_PITCH)._ceiling_label.text() == ""

    def test_warns_once_an_octave_shift_passes_the_ceiling(self, qt_app):
        dlg = _dialog(frequency=UNITY * 3)

        dlg._frequency.shift_octaves(1)

        assert "4.0" in dlg._ceiling_label.text()

    def test_clears_again_when_brought_back_down(self, qt_app):
        dlg = _dialog(frequency=UNITY * 3)

        dlg._frequency.shift_octaves(1)
        dlg._frequency.shift_octaves(-1)

        assert dlg._ceiling_label.text() == ""
