# coding: utf-8

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

INFO = "info"
SUCCESS = "success"
WARNING = "warning"
DANGER = "danger"

_EMOJI = {INFO: "ℹ️", SUCCESS: "✅", WARNING: "⚠️", DANGER: "⛔"}
_TRANSIENT = frozenset({INFO, SUCCESS})

DEFAULT_DISMISS_MS = 6000
MAX_VISIBLE = 3


class NotificationBar(QWidget):
    """Transient messages stacked at the top of the window.

    The result of an edit is news, not a question — reporting it through a
    modal dialog made every action cost an extra click and broke the flow of
    doing several in a row. Warnings and errors stay until dismissed, since
    those are worth reading; routine confirmations fade on their own."""

    def __init__(self, parent=None, dismiss_ms: int = DEFAULT_DISMISS_MS):
        super().__init__(parent)
        self._dismiss_ms = dismiss_ms
        self._rows: list[QWidget] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(6)
        self.setVisible(False)

    def push(self, message: str, severity: str = INFO) -> None:
        """Show a message. Info and success fade; warning and danger stay."""
        row = self._build_row(message, severity)
        self._rows.append(row)
        self._layout.addWidget(row)
        self.setVisible(True)

        while len(self._rows) > MAX_VISIBLE:
            self._dismiss(self._rows[0])

        if severity in _TRANSIENT:
            QTimer.singleShot(self._dismiss_ms, lambda: self._dismiss(row))

    def push_success(self, message: str) -> None:
        self.push(message, SUCCESS)

    def push_warning(self, message: str) -> None:
        self.push(message, WARNING)

    def push_danger(self, message: str) -> None:
        self.push(message, DANGER)

    def clear(self) -> None:
        for row in list(self._rows):
            self._dismiss(row)

    def messages(self) -> list[str]:
        """The text of what is currently on screen, newest last."""
        return [row.property("message") for row in self._rows]

    def _build_row(self, message: str, severity: str) -> QWidget:
        row = QWidget()
        row.setObjectName("notificationRow")
        row.setProperty("severity", severity)
        row.setProperty("message", message)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 9, 8, 9)
        layout.setSpacing(9)

        icon = QLabel(_EMOJI.get(severity, ""))
        icon.setObjectName("notificationIcon")
        layout.addWidget(icon)

        text = QLabel(message)
        text.setObjectName("notificationText")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(text, stretch=1)

        close = QPushButton("✕")
        close.setObjectName("notificationClose")
        close.setToolTip("Dismiss")
        close.setFixedWidth(32)
        close.clicked.connect(lambda: self._dismiss(row))
        layout.addWidget(close)

        return row

    def _dismiss(self, row: QWidget) -> None:
        if row not in self._rows:
            return

        self._rows.remove(row)
        self._layout.removeWidget(row)
        row.hide()
        row.deleteLater()

        if not self._rows:
            self.setVisible(False)
