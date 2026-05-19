# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QLabel, QRadioButton, QVBoxLayout,
)

from howl_editor.file_format_registry import FileFormat
from howl_editor.gui.layout import WindowSize


class ExportDialog(QDialog):

    def __init__(self, parent, target_label: str, options: list[FileFormat]):
        super().__init__(parent)
        self.setWindowTitle(f"Export {target_label}")
        self.resize(WindowSize.EXPORT_WIDTH, WindowSize.EXPORT_HEIGHT)
        self._options = options
        self._group = QButtonGroup(self)
        self._radios: list[QRadioButton] = []
        self._build_ui(target_label)

    def chosen_format(self) -> FileFormat | None:
        for i, radio in enumerate(self._radios):
            if radio.isChecked():
                return self._options[i]

        return None

    def _build_ui(self, target_label: str) -> None:
        layout = QVBoxLayout(self)

        prompt = QLabel(f"Choose a format to export {target_label} as:")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        for i, fmt in enumerate(self._options):
            radio = QRadioButton(f"{fmt.display_name}  ({fmt.extension})")

            if i == 0:
                radio.setChecked(True)

            self._group.addButton(radio, i)
            self._radios.append(radio)
            layout.addWidget(radio)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)
