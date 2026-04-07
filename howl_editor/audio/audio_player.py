# coding: utf-8

import hashlib
import tempfile
from pathlib import Path

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtCore import QUrl
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

_CACHE_DIR = Path(tempfile.gettempdir()) / "howl-editor"


class AudioPlayer:
    """Plays WAV audio data using Qt Multimedia with file caching."""

    def __init__(self):
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None

        if HAS_MULTIMEDIA:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)

        _CACHE_DIR.mkdir(exist_ok=True)

    @property
    def available(self) -> bool:
        return HAS_MULTIMEDIA and self._player is not None

    def play_wav(self, wav_data: bytes) -> None:
        if not self.available:
            return

        self.stop()

        checksum = hashlib.md5(wav_data).hexdigest()
        cached_path = _CACHE_DIR / f"{checksum}.wav"

        if not cached_path.exists():
            cached_path.write_bytes(wav_data)

        self._player.setSource(QUrl.fromLocalFile(str(cached_path)))
        self._player.play()

    def stop(self) -> None:
        if self._player:
            self._player.stop()

    def clear_cache(self) -> int:
        """Remove all cached WAV files. Returns number of files removed."""
        count = 0

        for f in _CACHE_DIR.glob("*.wav"):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass

        return count
