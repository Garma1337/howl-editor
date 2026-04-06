# coding: utf-8

import os
import tempfile

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtCore import QUrl
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False


class AudioPlayer:
    """Plays WAV audio data using Qt Multimedia."""

    def __init__(self):
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._temp_path: str | None = None

        if HAS_MULTIMEDIA:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)

    @property
    def available(self) -> bool:
        return HAS_MULTIMEDIA and self._player is not None

    def play_wav(self, wav_data: bytes) -> None:
        if not self.available:
            return

        self.stop()
        self._cleanup_temp()

        fd, self._temp_path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as f:
            f.write(wav_data)

        self._player.setSource(QUrl.fromLocalFile(self._temp_path))
        self._player.play()

    def stop(self) -> None:
        if self._player:
            self._player.stop()

    def _cleanup_temp(self) -> None:
        if self._temp_path and os.path.exists(self._temp_path):
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass

            self._temp_path = None
