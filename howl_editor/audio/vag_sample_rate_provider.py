# coding: utf-8


class VagSampleRateProvider:
    """Holds the default sample rate used when decoding VAG bytes to WAV
    on export paths that don't already know the rate (Export Sample as WAV,
    Export Bank Samples as WAV, Batch Export).

    Settable at runtime via the Tools menu. Persistence is the caller's job
    (MainWindow reads / writes QSettings on startup and on each change)."""

    PRESETS: tuple[int, ...] = (11025, 22050, 33075, 44100)
    DEFAULT_RATE = 11025

    def __init__(self, default: int = DEFAULT_RATE):
        self._rate = default if default in self.PRESETS else self.DEFAULT_RATE

    @property
    def rate(self) -> int:
        return self._rate

    def set(self, rate: int) -> None:
        if rate in self.PRESETS:
            self._rate = rate
