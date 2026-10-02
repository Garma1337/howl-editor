# coding: utf-8

"""These spawn real child processes: results, failures, progress and
cancellation all have to survive the trip across the process boundary.
"""

import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.background.process_runner import ProcessTaskRunner
from tests.gui.background import jobs_for_tests as jobs

TIMEOUT_SECONDS = 60


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def runner(qt_app):
    return ProcessTaskRunner(poll_interval_ms=5)


def _pump_until(qt_app, done, seconds: int = TIMEOUT_SECONDS) -> None:
    """Run the event loop until the job reports back, as the window would."""
    deadline = time.perf_counter() + seconds

    while not done and time.perf_counter() < deadline:
        qt_app.processEvents()


class TestResults:

    def test_a_result_comes_back_from_the_child(self, runner, qt_app):
        done = []

        runner.run(jobs.add, (2, 3), on_success=done.append)
        _pump_until(qt_app, done)

        assert done == [5]

    def test_a_failure_comes_back_as_a_message(self, runner, qt_app):
        errors = []

        runner.run(jobs.boom, on_error=errors.append)
        _pump_until(qt_app, errors)

        assert errors and "job went wrong" in errors[0]

    def test_a_failure_is_not_reported_as_success(self, runner, qt_app):
        done, errors = [], []

        runner.run(jobs.boom, on_success=done.append, on_error=errors.append)
        _pump_until(qt_app, errors)

        assert done == []


class TestProgress:

    def test_progress_crosses_the_process_boundary(self, runner, qt_app):
        done, seen = [], []

        runner.run(
            jobs.count_to, (500,),
            on_success=done.append, on_progress=lambda d, t: seen.append((d, t)),
        )
        _pump_until(qt_app, done)

        assert seen
        assert seen == sorted(seen)
        assert all(total == 500 for _done, total in seen)


class TestCancelling:

    def test_cancelling_stops_the_child(self, runner, qt_app):
        outcome, seen = [], []

        handle = runner.run(
            jobs.count_to, (2_000_000,),
            on_success=lambda result: outcome.append(("done", result)),
            on_cancelled=lambda: outcome.append(("cancelled",)),
            on_progress=lambda d, t: seen.append(d),
        )
        _pump_until(qt_app, seen)      # wait until it is genuinely running
        handle.cancel()
        _pump_until(qt_app, outcome)

        assert outcome == [("cancelled",)]

    def test_a_job_left_alone_is_not_reported_as_cancelled(self, runner, qt_app):
        outcome = []

        runner.run(
            jobs.add, (1, 1),
            on_success=lambda result: outcome.append(("done", result)),
            on_cancelled=lambda: outcome.append(("cancelled",)),
        )
        _pump_until(qt_app, outcome)

        assert outcome == [("done", 2)]


class TestSpawnFailure:
    """Pickling happens inside start(), on the spawn thread. A job that cannot
    cross the boundary has to report back — a busy row has no dismiss button,
    so a silent failure would leave it on screen forever.
    """

    def test_an_unpicklable_argument_is_reported_as_an_error(self, runner, qt_app):
        errors = []

        runner.run(jobs.add, (threading.Lock(), 1), on_error=errors.append)
        _pump_until(qt_app, errors)

        # The point is that it reports at all; the wording comes from whichever
        # layer refuses first.
        assert errors

    def test_an_unpicklable_argument_is_not_reported_as_success(self, runner, qt_app):
        done, errors = [], []

        runner.run(jobs.add, (threading.Lock(), 1), on_success=done.append, on_error=errors.append)
        _pump_until(qt_app, errors)

        assert done == []
