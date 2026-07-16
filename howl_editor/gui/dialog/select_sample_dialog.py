# coding: utf-8

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout,
)

from howl_editor.gui.layout import WindowSize


@dataclass(frozen=True)
class SampleChoice:
    """One row in the picker. `display` is the user-visible label, `spu_index`
    is what the caller wires back into the instrument/percussion entry."""
    spu_index: int
    display: str


class SelectSampleDialog(QDialog):

    def __init__(
        self,
        parent,
        title: str,
        prompt: str,
        choices: list[SampleChoice],
        current_spu_index: int | None = None,
        on_preview: Callable[[int], None] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(WindowSize.SELECT_SAMPLE_WIDTH, WindowSize.SELECT_SAMPLE_HEIGHT)
        self._choices = choices
        self._current = current_spu_index
        self._on_preview = on_preview
        self._build_ui(prompt)

    def chosen_spu_index(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None

        return item.data(Qt.UserRole)

    def _build_ui(self, prompt: str) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(prompt)
        header.setWordWrap(True)
        layout.addWidget(header)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter…")
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        self._populate()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        if self._on_preview is not None:
            row = QHBoxLayout()
            self._preview_button = QPushButton("▶️ Preview")
            self._preview_button.setToolTip(
                "Play the highlighted sample so you can hear it before picking.",
            )
            self._preview_button.clicked.connect(self._preview_selected)
            row.addWidget(self._preview_button)
            row.addStretch()
            row.addWidget(buttons)
            layout.addLayout(row)
        else:
            layout.addWidget(buttons, alignment=Qt.AlignRight)

    def _preview_selected(self) -> None:
        spu_index = self.chosen_spu_index()
        if spu_index is not None and self._on_preview is not None:
            self._on_preview(spu_index)

    def _populate(self) -> None:
        self._list.clear()

        for choice in self._choices:
            item = QListWidgetItem(choice.display)
            item.setData(Qt.UserRole, choice.spu_index)
            self._list.addItem(item)

            if choice.spu_index == self._current:
                self._list.setCurrentItem(item)

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setHidden(needle != "" and needle not in item.text().lower())
