# coding: utf-8

import multiprocessing as mp
import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer

from howl_editor.core.progress import Cancelled, ProgressReporter

POLL_INTERVAL_MS = 30

_PROGRESS = "progress"
_DONE = "done"
_FAILED = "failed"
_CANCELLED = "cancelled"


def _worker(func, args: tuple, kwargs: dict, queue, cancel_event) -> None:
    """Child-process entry point. Runs on a fresh interpreter, so it reports
    back over the queue instead of returning."""
    reporter = ProgressReporter(
        on_progress=lambda done, total: queue.put((_PROGRESS, done, total)),
        is_cancelled=cancel_event.is_set,
    )

    try:
        queue.put((_DONE, func(*args, **kwargs, progress=reporter)))
    except Cancelled:
        queue.put((_CANCELLED, None))
    except Exception as e:
        queue.put((_FAILED, f"{type(e).__name__}: {e}"))


class ProcessTaskHandle:
    """A running child process, from the starter's side."""

    def __init__(self, cancel_event, started: threading.Event):
        self._cancel_event = cancel_event
        self._started = started

    @property
    def has_started(self) -> bool:
        return self._started.is_set()

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()


class ProcessTaskRunner(QObject):
    """Runs a job in its own process and reports back on the GUI thread.

    A worker *thread* is not enough for pure-Python work: it holds the GIL and
    the window goes sluggish even though the work is 'in the background'. A
    separate interpreter has its own GIL, so the UI keeps every cycle it needs.

    `func` must be importable by name (a module-level function) and its
    arguments picklable — the child re-imports rather than forking on Windows.
    """

    def __init__(self, poll_interval_ms: int = POLL_INTERVAL_MS):
        super().__init__()
        self._poll_interval_ms = poll_interval_ms
        self._context = mp.get_context("spawn")

    def run(
        self,
        func: Callable[..., Any],
        args: tuple = (),
        kwargs: dict | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> ProcessTaskHandle:
        queue = self._context.Queue()
        cancel_event = self._context.Event()
        process = self._context.Process(
            target=_worker, args=(func, args, kwargs or {}, queue, cancel_event), daemon=True,
        )

        started = threading.Event()
        threading.Thread(
            target=lambda: self._spawn(process, queue, started), daemon=True,
        ).start()

        handle = ProcessTaskHandle(cancel_event, started)
        self._poll_until_done(
            queue, process, handle, on_success, on_error, on_cancelled, on_progress,
        )

        return handle

    def _spawn(self, process, queue, started: threading.Event) -> None:
        """Start the child off the caller's thread: spawning costs ~240 ms on
        Windows (a fresh interpreter re-imports everything), and that lands on
        whichever thread calls start() — the exact stall this class exists to
        avoid. A start that fails (an argument that will not pickle, no room
        for another process) has to be reported, or the poller would wait on a
        child that never existed."""
        try:
            process.start()
        except Exception as e:
            queue.put((_FAILED, f"{type(e).__name__}: {e}"))
        finally:
            started.set()

    def _poll_until_done(
        self, queue, process, handle, on_success, on_error, on_cancelled, on_progress,
    ) -> None:
        """Drain the child's messages from the GUI thread. Polling costs
        nothing next to the work being waited on, and keeps every callback on
        the thread that owns the widgets."""
        timer = QTimer(self)
        timer.setInterval(self._poll_interval_ms)

        def finish(callback, *callback_args) -> None:
            timer.stop()
            timer.deleteLater()

            # A child whose start failed was never alive, and join() refuses
            # one of those; is_alive() reaps an exited one on its own.
            if process.is_alive():
                process.join(timeout=1)

            # The queue owns a pipe and a lock; a window renders hundreds of
            # songs in a session, so each one has to be handed back.
            queue.close()

            if callback is not None:
                callback(*callback_args)

        def poll() -> None:
            while not queue.empty():
                kind, *payload = queue.get()

                if kind == _PROGRESS and on_progress is not None:
                    on_progress(*payload)
                elif kind == _DONE:
                    finish(on_success, payload[0])
                    return
                elif kind == _FAILED:
                    finish(on_error, payload[0])
                    return
                elif kind == _CANCELLED:
                    finish(on_cancelled)
                    return

            if handle.has_started and not process.is_alive():
                # Died without reporting — killed from outside, or crashed.
                finish(on_cancelled if handle.is_cancelled else on_error, *(
                    () if handle.is_cancelled else ("the render process stopped unexpectedly",)
                ))

        timer.timeout.connect(poll)
        timer.start()
