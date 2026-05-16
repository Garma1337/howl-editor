# coding: utf-8

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QMessageBox, QVBoxLayout,
)


@dataclass
class SaphiExportSelection:
    bank_index: int
    song_index: int
    name: str
    author: str


class SaphiExportDialog(QDialog):
    """Collects bank, song, and metadata for a .sca export."""

    def __init__(self, parent, bank_labels: list[str], song_labels: list[str],
                 bank_sizes: list[int], bank_max_size: int):
        super().__init__(parent)
        self.setWindowTitle("Export for Saphi")
        self.resize(420, 220)

        self._bank_sizes = bank_sizes
        self._bank_max_size = bank_max_size

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_form(bank_labels, song_labels))
        self._size_warning = QLabel("")
        self._size_warning.setStyleSheet("color: #c97a00;")
        self._size_warning.setVisible(False)
        layout.addWidget(self._size_warning)
        layout.addWidget(self._build_buttons())

        self._bank_combo.currentIndexChanged.connect(self._refresh_size_warning)
        self._refresh_size_warning()

    def _build_form(self, bank_labels: list[str], song_labels: list[str]) -> QFormLayout:
        form = QFormLayout()
        self._bank_combo = QComboBox()
        for i, label in enumerate(bank_labels):
            self._bank_combo.addItem(label, i)

        form.addRow("Bank:", self._bank_combo)

        self._song_combo = QComboBox()
        for i, label in enumerate(song_labels):
            self._song_combo.addItem(label, i)

        form.addRow("Song:", self._song_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(64)
        form.addRow("Name:", self._name_edit)

        self._author_edit = QLineEdit()
        self._author_edit.setMaxLength(64)
        form.addRow("Author:", self._author_edit)

        return form

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Export...")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def _refresh_size_warning(self) -> None:
        idx = self._bank_combo.currentData()

        if idx is None or idx >= len(self._bank_sizes):
            self._size_warning.setVisible(False)
            return

        size = self._bank_sizes[idx]
        if size > self._bank_max_size:
            self._size_warning.setText(
                f"⚠ Bank is {size} bytes ({size / 1024:.1f} KB) — "
                f"exceeds Saphi limit of {self._bank_max_size} bytes "
                f"({self._bank_max_size / 1024:.0f} KB). Saphi will reject this file."
            )
            self._size_warning.setVisible(True)
        else:
            self._size_warning.setVisible(False)

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "Required field", "Name is required.")
            return

        if not self._author_edit.text().strip():
            QMessageBox.warning(self, "Required field", "Author is required.")
            return

        bank_idx = self._bank_combo.currentData()

        if bank_idx is not None and bank_idx < len(self._bank_sizes) and self._bank_sizes[bank_idx] > self._bank_max_size:
            confirm = QMessageBox.warning(
                self, "Bank exceeds Saphi limit",
                f"The selected bank is {self._bank_sizes[bank_idx]} bytes, which is "
                f"larger than Saphi's {self._bank_max_size}-byte limit. The exported "
                f".sca file will be rejected by the Saphi Client.\n\nExport anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )

            if confirm != QMessageBox.Yes:
                return

        self.accept()

    def get_selection(self) -> SaphiExportSelection:
        return SaphiExportSelection(
            bank_index=self._bank_combo.currentData(),
            song_index=self._song_combo.currentData(),
            name=self._name_edit.text().strip(),
            author=self._author_edit.text().strip(),
        )
