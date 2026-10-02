# coding: utf-8

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

BUSY = "busy"
INFO = "info"
SUCCESS = "success"
WARNING = "warning"
DANGER = "danger"

_EMOJI = {BUSY: "⏳", INFO: "ℹ️", SUCCESS: "✅", WARNING: "⚠️", DANGER: "⛔"}
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
        self._append(row)

        if severity in _TRANSIENT:
            QTimer.singleShot(self._dismiss_ms, lambda: self._dismiss(row))

    def push_success(self, message: str) -> None:
        self.push(message, SUCCESS)

    def push_warning(self, message: str) -> None:
        self.push(message, WARNING)

    def push_danger(self, message: str) -> None:
        self.push(message, DANGER)

    def push_busy(self, message: str, on_cancel=None) -> "BusyNotification":
        """Show work in progress. The handle replaces the row with the result,
        so a long job is visible from start to finish in the same place.
        With `on_cancel` the row offers a Cancel button."""
        row = self._build_row(message, BUSY)

        bar = QProgressBar()
        bar.setObjectName("notificationProgress")
        bar.setRange(0, 0)   # indeterminate until the work reports a total
        bar.setTextVisible(False)
        bar.setFixedWidth(120)
        # A busy row has no dismiss button, so there is nothing to insert
        # before: the bar belongs after the message, at the end of the row.
        row.layout().addWidget(bar)

        self._append(row)
        handle = BusyNotification(self, row, bar)

        if on_cancel is not None:
            handle.set_cancel(on_cancel)

        return handle

    def clear(self) -> None:
        for row in list(self._rows):
            self._dismiss(row)

    def messages(self) -> list[str]:
        """The text of what is currently on screen, newest last."""
        return [row.property("message") for row in self._rows]

    def _append(self, row: QWidget) -> None:
        self._rows.append(row)
        self._layout.addWidget(row)
        self.setVisible(True)
        self._trim()

    def _trim(self) -> None:
        """Drop the oldest finished message. A running job keeps its row: it
        is the only sign the work is still going."""
        while len(self._rows) > MAX_VISIBLE:
            oldest = next(
                (row for row in self._rows if row.property("severity") != BUSY), None,
            )

            if oldest is None:
                return

            self._dismiss(oldest)

    def is_showing(self, row: QWidget) -> bool:
        return row in self._rows

    def dismiss(self, row: QWidget) -> None:
        self._dismiss(row)

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

        if severity != BUSY:
            # A running job's row has no dismiss button: it ends on its own,
            # and closing it early would delete widgets the job still writes
            # progress into. Cancel is the way to stop one.
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


class BusyNotification:
    """A running job's row. Finishing swaps it for the outcome."""

    def __init__(self, bar: NotificationBar, row: QWidget, progress: QProgressBar):
        self._bar = bar
        self._row = row
        self._progress = progress

    def set_cancel(self, on_cancel) -> None:
        """Offer to stop the job. Added after the row exists, because the
        handle that can cancel only comes back once the job has started."""
        if not self._is_live():
            return

        button = QPushButton("Cancel")
        button.setObjectName("notificationCancel")
        button.clicked.connect(on_cancel)
        self._row.layout().addWidget(button)

    def set_progress(self, done: int, total: int) -> None:
        """Switch from the indeterminate sweep to a real share of the work.

        A job keeps reporting for a moment after its row is gone — cancelling
        races the updates already in flight — and the widgets behind it are
        deleted by then, so a stale handle quietly does nothing."""
        if total <= 0 or not self._is_live():
            return

        # QProgressBar ignores a value outside its range, so an estimated
        # total the job overshoots would freeze the bar instead of filling it.
        self._progress.setRange(0, total)
        self._progress.setValue(min(done, total))

    def _is_live(self) -> bool:
        return self._bar.is_showing(self._row)

    def succeeded(self, message: str) -> None:
        self._replace_with(message, SUCCESS)

    def failed(self, message: str) -> None:
        self._replace_with(message, DANGER)

    def dismiss(self) -> None:
        self._bar.dismiss(self._row)

    def _replace_with(self, message: str, severity: str) -> None:
        self.dismiss()
        self._bar.push(message, severity)
