# coding: utf-8

import gc
import os
import weakref

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton

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


def _octave_button(dialog: EditInstrumentDialog, direction: str) -> QPushButton:
    return next(
        button for button in dialog.findChildren(QPushButton)
        if "Octave" in button.text() and direction in button.text()
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


class TestOctaveButtonClicks:
    """The buttons carry the pitch edit a music maker actually makes, and they
    are wired to the spin box's own slots rather than to the dialog."""

    def test_clicking_up_doubles_the_pitch(self, qt_app):
        dlg = _dialog()

        _octave_button(dlg, "up").click()

        assert dlg.chosen().frequency == 2 * UNITY

    def test_clicking_down_halves_the_pitch(self, qt_app):
        dlg = _dialog()

        _octave_button(dlg, "down").click()

        assert dlg.chosen().frequency == UNITY // 2

    def test_clicks_accumulate(self, qt_app):
        dlg = _dialog(frequency=UNITY // 4)

        _octave_button(dlg, "up").click()
        _octave_button(dlg, "up").click()

        assert dlg.chosen().frequency == UNITY

    def test_clicking_up_stops_at_the_ceiling(self, qt_app):
        """Clamping to the on-disc field instead let this climb to 16x."""
        dlg = _dialog()

        for _ in range(5):
            _octave_button(dlg, "up").click()

        assert dlg.chosen().frequency == spu.MAX_PITCH


class TestLifetime:

    def test_dropping_the_dialog_frees_it_without_the_cyclic_collector(self, qt_app):
        """A parentless dialog must die by reference count alone."""
        gc.collect()
        dialog = _dialog()
        ref = weakref.ref(dialog)

        gc.disable()
        try:
            del dialog
            assert ref() is None, "dialog outlived its last reference - it is in a cycle"
        finally:
            gc.enable()


class TestCeilingWarning:

    def test_quiet_below_the_ceiling(self, qt_app):
        assert _dialog(frequency=spu.MAX_PITCH)._ceiling_label.text() == ""

    def test_warns_about_a_register_typed_above_the_ceiling(self, qt_app):
        """Stepping cannot pass the ceiling, but the field holds four times
        what the console plays, so a typed value still can."""
        dlg = _dialog()

        dlg._frequency.setValue(spu.MAX_PITCH + 1)

        assert "4.0" in dlg._ceiling_label.text()

    def test_stepping_up_never_raises_the_warning(self, qt_app):
        dlg = _dialog(frequency=UNITY * 3)

        dlg._frequency.shift_octaves(1)

        assert dlg._ceiling_label.text() == ""

    def test_clears_again_when_brought_back_down(self, qt_app):
        dlg = _dialog()

        dlg._frequency.setValue(spu.MAX_PITCH + 1)
        dlg._frequency.shift_octaves(-1)

        assert dlg._ceiling_label.text() == ""
