# coding: utf-8

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False


class PlayerWidget(QWidget):
    """Audio transport bar with play/stop buttons, track label, and elapsed time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_player: QMediaPlayer | None = None
        self._replay_callback = None
        self._stop_callback = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self._play_btn = QPushButton("\u25B6")
        self._play_btn.setFixedWidth(32)
        self._play_btn.setToolTip("Play")
        self._play_btn.clicked.connect(self._on_play)
        layout.addWidget(self._play_btn)

        self._stop_btn = QPushButton("\u25A0")
        self._stop_btn.setFixedWidth(32)
        self._stop_btn.setToolTip("Stop")
        self._stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self._stop_btn)

        self._label = QLabel("No audio")
        self._label.setMinimumWidth(100)
        layout.addWidget(self._label, stretch=1)

        self._time_label = QLabel("0:00")
        self._time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label.setFixedWidth(50)
        layout.addWidget(self._time_label)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._update_time)

        self._update_buttons(False)

    def connect_player(self, media_player, stop_callback) -> None:
        """Connect to a QMediaPlayer to track playback state and position."""
        self._media_player = media_player
        self._stop_callback = stop_callback

        if HAS_MULTIMEDIA and media_player:
            media_player.playbackStateChanged.connect(self._on_state_changed)

    def set_now_playing(self, label: str, replay_callback=None) -> None:
        """Show a track label and start the elapsed timer."""
        self._label.setText(label)
        self._replay_callback = replay_callback
        self._time_label.setText("0:00")
        self._timer.start()
        self._update_buttons(True)

    def clear(self) -> None:
        """Reset the player bar to idle state."""
        self._label.setText("No audio")
        self._time_label.setText("0:00")
        self._replay_callback = None
        self._timer.stop()
        self._update_buttons(False)

    def _on_play(self) -> None:
        if self._replay_callback:
            self._replay_callback()

    def _on_stop(self) -> None:
        if self._stop_callback:
            self._stop_callback()

        self.clear()

    def _on_state_changed(self, state) -> None:
        if HAS_MULTIMEDIA and state == QMediaPlayer.PlaybackState.StoppedState:
            self._timer.stop()
            self._update_buttons(False)

    def _update_time(self) -> None:
        if not self._media_player:
            return

        pos_ms = self._media_player.position()
        seconds = pos_ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        self._time_label.setText(f"{minutes}:{secs:02d}")

    def _update_buttons(self, playing: bool) -> None:
        self._play_btn.setEnabled(not playing and self._replay_callback is not None)
        self._stop_btn.setEnabled(playing)
