# coding: utf-8

from collections.abc import Callable


class Cancelled(Exception):
    """Raised inside a job when the user asked it to stop."""


class ProgressReporter:
    """How a long job talks to whoever started it.

    Kept free of Qt so the renderer and the exporters can accept one without
    knowing a GUI exists; tests pass a bare reporter, or none at all."""

    def __init__(
        self,
        on_progress: Callable[[int, int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ):
        self._on_progress = on_progress
        self._is_cancelled = is_cancelled

    @property
    def cancelled(self) -> bool:
        return self._is_cancelled is not None and self._is_cancelled()

    def report(self, done: int, total: int) -> None:
        if self._on_progress is not None:
            self._on_progress(done, total)

    def check(self) -> None:
        """Abandon the job if it has been cancelled. Call it somewhere the
        work can be dropped safely — the result is discarded either way."""
        if self.cancelled:
            raise Cancelled()

    def step(self, done: int, total: int) -> None:
        """Report progress and bail out if cancelled, the usual pairing."""
        self.report(done, total)
        self.check()
