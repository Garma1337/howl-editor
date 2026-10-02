# coding: utf-8

import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from howl_editor.core.progress import Cancelled, ProgressReporter


class _TaskSignals(QObject):
    """Signals live on a QObject because QRunnable is not one."""
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progressed = Signal(int, int)


class TaskHandle:
    """A running job, from the starter's side."""

    def __init__(self, cancel_flag: threading.Event):
        self._cancel_flag = cancel_flag

    def cancel(self) -> None:
        self._cancel_flag.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_flag.is_set()


class _Task(QRunnable):
    def __init__(self, work, signals: _TaskSignals, reporter: ProgressReporter):
        super().__init__()
        self._work = work
        self._signals = signals
        self._reporter = reporter

    def run(self) -> None:
        try:
            result = self._work(self._reporter)
        except Cancelled:
            self._signals.cancelled.emit()
            return
        except Exception as e:
            self._signals.failed.emit(str(e))
            return

        self._signals.succeeded.emit(result)


class TaskRunner(QObject):
    """Runs slow work off the GUI thread, one job at a time.

    Rendering a song takes seconds, and doing it inline freezes everything.
    The pool is deliberately single-threaded: the renderer and the sample
    caches are shared mutable state, and queuing is cheaper than making every
    one of them thread-safe for a gain nobody asked for.

    `work` runs on a worker thread and is handed a ProgressReporter, so it must
    not touch widgets; the callbacks run on the GUI thread and may."""

    def __init__(self):
        super().__init__()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)
        self._live: list[_TaskSignals] = []

    def run(
        self,
        work: Callable[[ProgressReporter], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> TaskHandle:
        signals = _TaskSignals()
        # Keep the signals object alive until the task reports back; nothing
        # else holds a reference once run() returns.
        self._live.append(signals)

        cancel_flag = threading.Event()
        reporter = ProgressReporter(
            on_progress=signals.progressed.emit, is_cancelled=cancel_flag.is_set,
        )

        def finish(callback, *args) -> None:
            self._retire(signals)

            if callback is not None:
                callback(*args)

        signals.succeeded.connect(lambda result: finish(on_success, result))
        signals.failed.connect(lambda message: finish(on_error, message))
        signals.cancelled.connect(lambda: finish(on_cancelled))

        if on_progress is not None:
            signals.progressed.connect(on_progress)

        self._pool.start(_Task(work, signals, reporter))

        return TaskHandle(cancel_flag)

    def wait_for_done(self, timeout_ms: int = 30_000) -> bool:
        """Block until the queue drains — for tests and for shutdown."""
        return self._pool.waitForDone(timeout_ms)

    def _retire(self, signals: _TaskSignals) -> None:
        if signals in self._live:
            self._live.remove(signals)
