# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout,
)

from howl_editor.gui.layout import WindowSize


@dataclass(frozen=True)
class CopyTargetContainer:
    """One option for the outer ('container') picker — a target bank or song
    plus the human-readable labels of its existing children."""
    index: int
    display: str
    child_labels: tuple[str, ...]


@dataclass(frozen=True)
class CopyTarget:
    container_index: int
    child_index: int | None  # None => append a new child


class CopyTargetDialog(QDialog):
    """Generic 'copy X into Y' picker: choose a target container and either
    append as a new child or replace one of its existing children. Used by
    both 'copy sample to bank' and 'copy sequence to song' flows — the labels
    distinguish the two."""

    def __init__(
        self,
        parent,
        title: str,
        prompt: str,
        container_label: str,
        child_label: str,
        append_label: str,
        containers: list[CopyTargetContainer],
        source_container_index: int,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(WindowSize.COPY_SAMPLE_WIDTH, WindowSize.COPY_SAMPLE_HEIGHT)
        self._containers = containers
        self._source_container_index = source_container_index
        self._append_label = append_label
        self._build_ui(prompt, container_label, child_label)

    def chosen_target(self) -> CopyTarget | None:
        container = self._selected_container()
        if container is None:
            return None

        return CopyTarget(
            container_index=container.index,
            child_index=self._child_combo.currentData(),
        )

    def _build_ui(self, prompt: str, container_label: str, child_label: str) -> None:
        layout = QVBoxLayout(self)

        label = QLabel(prompt)
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QFormLayout()
        layout.addLayout(form)

        self._container_combo = QComboBox()
        for container in self._containers:
            self._container_combo.addItem(container.display, container.index)

        default_idx = next(
            (i for i, c in enumerate(self._containers) if c.index != self._source_container_index),
            0,
        )
        self._container_combo.setCurrentIndex(default_idx)
        self._container_combo.currentIndexChanged.connect(self._refresh_child_combo)
        form.addRow(container_label, self._container_combo)

        self._child_combo = QComboBox()
        form.addRow(child_label, self._child_combo)
        self._refresh_child_combo()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)

    def _selected_container(self) -> CopyTargetContainer | None:
        idx = self._container_combo.currentIndex()
        if 0 <= idx < len(self._containers):
            return self._containers[idx]

        return None

    def _refresh_child_combo(self) -> None:
        self._child_combo.clear()
        self._child_combo.addItem(self._append_label, None)

        container = self._selected_container()
        if container is None:
            return

        for slot, label in enumerate(container.child_labels):
            self._child_combo.addItem(label, slot)
