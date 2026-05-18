# coding: utf-8

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QWidget, QHBoxLayout, QPushButton, QLabel, QSlider

try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False


class PlayerWidget(QWidget):
    """Audio transport bar with play/stop buttons, seek slider, and elapsed
    time, plus a Loop toggle.

    Looping is delegated to the underlying
    QMediaPlayer (`setLoops(Infinite)`) so a song repeats gapless without
    re-rendering the WAV in Python."""

    sig_active_changed = Signal(bool)
    sig_loop_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_player: QMediaPlayer | None = None
        self._replay_callback = None
        self._stop_callback = None
        self._loop_callback = None
        self._seeking = False
        self._user_stopped = False

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

        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setEnabled(False)
        self._seek_slider.sliderPressed.connect(self._on_seek_start)
        self._seek_slider.sliderReleased.connect(self._on_seek_end)
        layout.addWidget(self._seek_slider, stretch=2)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label.setFixedWidth(90)
        layout.addWidget(self._time_label)

        self._loop_check = QCheckBox("\uD83D\uDD01  Loop")
        self._loop_check.setToolTip("Repeat the current track when it finishes.")
        self._loop_check.toggled.connect(self._on_loop_toggled)
        layout.addWidget(self._loop_check)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._update_time)

        self._update_buttons(False)

    def connect_player(self, media_player, stop_callback, loop_callback=None) -> None:
        self._media_player = media_player
        self._stop_callback = stop_callback
        self._loop_callback = loop_callback

        if HAS_MULTIMEDIA and media_player:
            media_player.playbackStateChanged.connect(self._on_state_changed)
            media_player.mediaStatusChanged.connect(self._on_media_status_changed)

    def set_now_playing(self, label: str, replay_callback=None) -> None:
        """Show a track label and start the elapsed timer."""
        self._label.setText(label)
        self._replay_callback = replay_callback
        self._time_label.setText("0:00 / 0:00")
        self._seek_slider.setValue(0)
        self._user_stopped = False
        self._timer.start()
        self._update_buttons(True)
        self._apply_loop_state()
        self.sig_active_changed.emit(True)

    def is_looping(self) -> bool:
        return self._loop_check.isChecked()

    def is_active(self) -> bool:
        """True between set_now_playing() and clear() — useful for parents
        that want to show/hide a dock container based on actual activity."""
        return self._replay_callback is not None

    def set_loop_enabled(self, enabled: bool) -> None:
        self._loop_check.setChecked(enabled)

    def clear(self) -> None:
        """Reset the player bar to idle state."""
        self._label.setText("No audio")
        self._time_label.setText("0:00 / 0:00")
        self._seek_slider.setValue(0)
        self._replay_callback = None
        self._timer.stop()
        self._update_buttons(False)
        self.sig_active_changed.emit(False)

    def _on_play(self) -> None:
        if self._replay_callback:
            self._replay_callback()

    def _on_stop(self) -> None:
        self._user_stopped = True

        if self._stop_callback:
            self._stop_callback()

        self.clear()

    def _on_state_changed(self, state) -> None:
        if HAS_MULTIMEDIA and state == QMediaPlayer.PlaybackState.StoppedState:
            self._timer.stop()
            self._update_buttons(False)

    def _on_media_status_changed(self, status) -> None:
        if not HAS_MULTIMEDIA:
            return

        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return

        if self._user_stopped or self.is_looping():
            return

        self.clear()

    def _on_loop_toggled(self, checked: bool) -> None:
        self.sig_loop_toggled.emit(checked)
        self._apply_loop_state()

    def _apply_loop_state(self) -> None:
        if self._loop_callback is not None:
            self._loop_callback(self.is_looping())

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False

        if not self._media_player:
            return

        dur = self._media_player.duration()
        if dur > 0:
            target = self._seek_slider.value() * dur // 1000
            self._media_player.setPosition(target)

    def _update_time(self) -> None:
        if not self._media_player:
            return

        pos_ms = self._media_player.position()
        dur_ms = self._media_player.duration()

        pos_text = self._format_time(pos_ms)
        dur_text = self._format_time(dur_ms)
        self._time_label.setText(f"{pos_text} / {dur_text}")

        if not self._seeking and dur_ms > 0:
            self._seek_slider.setValue(int(pos_ms * 1000 / dur_ms))

    def _format_time(self, ms: int) -> str:
        seconds = ms // 1000
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _update_buttons(self, playing: bool) -> None:
        self._play_btn.setEnabled(not playing and self._replay_callback is not None)
        self._stop_btn.setEnabled(playing)
        self._seek_slider.setEnabled(playing)
