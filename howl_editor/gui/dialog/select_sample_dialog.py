# coding: utf-8

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout,
)

from howl_editor.gui.layout import WindowSize
from howl_editor.gui.sample_choice import SampleChoice

__all__ = ["SampleChoice", "SelectSampleDialog"]


class SelectSampleDialog(QDialog):

    FREE_MARK = "  ·  🆓 free"

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

        selected = False

        for choice in self._choices:
            item = QListWidgetItem(self._label(choice))
            item.setData(Qt.UserRole, choice.spu_index)

            if choice.tooltip:
                item.setToolTip(choice.tooltip)

            if not choice.enabled:
                item.setFlags(item.flags() & ~(Qt.ItemIsEnabled | Qt.ItemIsSelectable))

            self._list.addItem(item)

            if not selected and choice.enabled and choice.spu_index == self._current:
                self._list.setCurrentItem(item)
                self._list.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                selected = True

    def _label(self, choice: SampleChoice) -> str:
        return choice.display + self.FREE_MARK if choice.free else choice.display

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setHidden(needle != "" and needle not in item.text().lower())
