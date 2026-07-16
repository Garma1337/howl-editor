# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout,
)

from howl_editor.ctr.diagnostics.howl_diagnostics import DiagnosisReport, Severity
from howl_editor.gui.severity_presenter import SeverityPresenter


class DiagnosisReportDialog(QDialog):
    """Shows a whole-file diagnosis: a severity-count header and every finding,
    most severe first, with a button to copy the report as plain text."""

    def __init__(self, parent, report: DiagnosisReport, severity_presenter: SeverityPresenter | None = None):
        super().__init__(parent)
        self.setWindowTitle("HOWL Diagnosis")
        self.resize(720, 480)
        self._report = report
        self._presenter = severity_presenter or SeverityPresenter()
        self._build_ui()

    def _icon(self, severity: Severity) -> str:
        return self._presenter.emoji(severity)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        counts = self._report.counts()
        header = QLabel(
            f"{self._icon(Severity.ERROR)} {counts[Severity.ERROR]} errors      "
            f"{self._icon(Severity.WARNING)} {counts[Severity.WARNING]} warnings      "
            f"{self._icon(Severity.INFO)} {counts[Severity.INFO]} info"
        )
        layout.addWidget(header)

        if counts[Severity.ERROR] == 0 and counts[Severity.WARNING] == 0:
            subtitle = QLabel("No issues found. 🎉")
        else:
            subtitle = QLabel("Items that may crash the game or sound wrong in-game:")

        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._list = QListWidget()
        self._list.setWordWrap(True)
        layout.addWidget(self._list, stretch=1)
        self._populate()

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        copy_button = QPushButton("Copy to clipboard")
        copy_button.clicked.connect(self._copy_to_clipboard)

        row = QHBoxLayout()
        row.addWidget(copy_button)
        row.addStretch()
        row.addWidget(buttons)
        layout.addLayout(row)

    def _populate(self) -> None:
        for finding in self._report.findings:
            icon = self._icon(finding.severity)
            item = QListWidgetItem(f"{icon}  [{finding.category.value}]  {finding.message}")
            self._list.addItem(item)

    def _plain_text(self) -> str:
        lines = []
        counts = self._report.counts()
        lines.append(
            f"HOWL Diagnosis — {counts[Severity.ERROR]} errors, "
            f"{counts[Severity.WARNING]} warnings, {counts[Severity.INFO]} info"
        )
        lines.append("")
        for finding in self._report.findings:
            lines.append(f"[{finding.severity.name}] {finding.category.value}: {finding.message}")
        return "\n".join(lines)

    def _copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self._plain_text())
