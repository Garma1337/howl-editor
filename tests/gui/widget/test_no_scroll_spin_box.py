# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from howl_editor.gui.widget.no_scroll_spin_box import NoScrollSpinBox


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _wheel_event() -> QWheelEvent:
    return QWheelEvent(
        QPoint(0, 0), QPoint(0, 0), QPoint(0, 0), QPoint(0, -120),
        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False,
    )


class TestNoScrollSpinBox:

    def test_wheel_ignored_without_focus(self, qt_app):
        box = NoScrollSpinBox()
        box.setRange(0, 100)
        box.setValue(10)

        box.wheelEvent(_wheel_event())

        assert box.value() == 10

    def test_wheel_applied_with_focus(self, qt_app):
        box = NoScrollSpinBox()
        box.setRange(0, 100)
        box.setValue(10)
        box.setFocus()
        # In the offscreen/minimal platform a widget may not actually grab
        # focus; only assert wheel behaviour when it did.
        if not box.hasFocus():
            pytest.skip("widget could not take focus on this platform")

        box.wheelEvent(_wheel_event())

        assert box.value() != 10

    def test_uses_strong_focus_policy(self, qt_app):
        # StrongFocus (not the default WheelFocus) stops the wheel from
        # focusing — and then editing — the box on hover.
        assert NoScrollSpinBox().focusPolicy() == Qt.StrongFocus
