# coding: utf-8

from struct import unpack_from

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


_WAVEFORM_COLOR = QColor(76, 175, 80)
_CENTER_LINE_COLOR = QColor(100, 100, 100)
_LOOP_MARKER_COLOR = QColor(255, 152, 0)
_BACKGROUND_COLOR = QColor(30, 30, 30)
_SAMPLE_MAX = 32768.0
_WAV_HEADER_SIZE = 44


class WaveformWidget(QWidget):
    """Displays a PCM waveform with optional loop-start marker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: list[int] = []
        self._loop_start: int = -1
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

    def set_wav(self, wav_data: bytes) -> None:
        """Extract mono samples from WAV bytes and display the waveform."""
        if len(wav_data) < _WAV_HEADER_SIZE:
            self.clear()
            return

        channels = unpack_from("<H", wav_data, 22)[0]
        data_start = _WAV_HEADER_SIZE
        pcm = wav_data[data_start:]

        if channels == 2:
            # Average stereo L+R to mono
            num_frames = len(pcm) // 4
            self._samples = [
                (unpack_from("<hh", pcm, i * 4)[0] + unpack_from("<hh", pcm, i * 4)[1]) // 2
                for i in range(num_frames)
            ]
        else:
            num_samples = len(pcm) // 2
            self._samples = [unpack_from("<h", pcm, i * 2)[0] for i in range(num_samples)]

        self._loop_start = -1
        self.update()

    def set_samples(self, samples: list[int], loop_start: int = -1) -> None:
        """Set raw PCM samples directly (used for sample selection preview)."""
        self._samples = samples
        self._loop_start = loop_start
        self.update()

    def clear(self) -> None:
        self._samples = []
        self._loop_start = -1
        self.update()

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 80)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, _BACKGROUND_COLOR)

        mid_y = h / 2

        # Center line
        painter.setPen(QPen(_CENTER_LINE_COLOR, 1))
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        if not self._samples or w < 2:
            painter.end()
            return

        num_samples = len(self._samples)
        painter.setPen(QPen(_WAVEFORM_COLOR, 1))

        # Draw min/max per pixel column for efficient rendering
        for x in range(w):
            start = x * num_samples // w
            end = max(start + 1, (x + 1) * num_samples // w)
            end = min(end, num_samples)

            chunk = self._samples[start:end]
            lo = min(chunk)
            hi = max(chunk)

            y_top = int(mid_y - (hi / _SAMPLE_MAX) * mid_y)
            y_bot = int(mid_y - (lo / _SAMPLE_MAX) * mid_y)

            if y_top == y_bot:
                painter.drawPoint(x, y_top)
            else:
                painter.drawLine(x, y_top, x, y_bot)

        # Loop start marker
        if 0 <= self._loop_start < num_samples:
            loop_x = int(self._loop_start * w / num_samples)
            painter.setPen(QPen(_LOOP_MARKER_COLOR, 1, Qt.DashLine))
            painter.drawLine(loop_x, 0, loop_x, h)

        painter.end()
