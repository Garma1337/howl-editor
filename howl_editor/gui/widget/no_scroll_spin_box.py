# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox


class NoScrollSpinBox(QSpinBox):
    """A spin box that only responds to the mouse wheel while it holds keyboard
    focus.

    In a table of these (e.g. the MIDI-import mapping grid) the default spin box
    grabs wheel events just by being hovered, so scrolling the list silently
    counts values up or down. StrongFocus stops the wheel from focusing the box,
    and ignoring the wheel while unfocused lets the scroll pass through to the
    table instead of editing a value the user never meant to touch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
