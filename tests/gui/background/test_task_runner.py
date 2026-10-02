# coding: utf-8

import os
import threading

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.background.task_runner import TaskRunner


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def runner(qt_app):
    return TaskRunner()


def _settle(runner, qt_app) -> None:
    """Let the worker finish, then deliver its queued signals."""
    runner.wait_for_done()
    qt_app.processEvents()


class TestRunning:

    def test_the_result_reaches_the_callback(self, runner, qt_app):
        results = []

        runner.run(lambda _progress: 6 * 7, results.append)
        _settle(runner, qt_app)

        assert results == [42]

    def test_the_work_runs_off_the_calling_thread(self, runner, qt_app):
        where = {}

        runner.run(lambda _p: threading.current_thread().ident, where.setdefault)
        _settle(runner, qt_app)

        assert where and threading.current_thread().ident not in where

    def test_callbacks_run_on_the_calling_thread(self, runner, qt_app):
        # Callbacks touch widgets, so they must come back to the GUI thread.
        seen = []

        runner.run(lambda _p: None, lambda _result: seen.append(threading.current_thread().ident))
        _settle(runner, qt_app)

        assert seen == [threading.current_thread().ident]


class TestFailing:

    def test_an_exception_is_reported_not_raised(self, runner, qt_app):
        errors = []

        runner.run(lambda _p: 1 / 0, lambda _result: None, errors.append)
        _settle(runner, qt_app)

        assert errors and "division by zero" in errors[0]

    def test_success_is_not_reported_when_the_work_fails(self, runner, qt_app):
        results = []

        runner.run(lambda _p: 1 / 0, results.append, lambda _message: None)
        _settle(runner, qt_app)

        assert results == []

    def test_a_failure_without_an_error_callback_is_swallowed(self, runner, qt_app):
        runner.run(lambda _p: 1 / 0, lambda _result: None)

        _settle(runner, qt_app)


class TestQueueing:

    def test_jobs_run_one_at_a_time_in_order(self, runner, qt_app):
        # The renderer and the sample caches are shared, so overlap would race.
        order = []

        for i in range(4):
            runner.run(lambda _p, i=i: order.append(i), lambda _result: None)

        _settle(runner, qt_app)

        assert order == [0, 1, 2, 3]


class TestProgress:

    def test_what_the_work_reports_reaches_the_callback(self, runner, qt_app):
        seen = []

        def work(progress):
            for done in range(1, 4):
                progress.report(done, 3)

        runner.run(work, lambda _result: None, on_progress=lambda d, t: seen.append((d, t)))
        _settle(runner, qt_app)

        assert seen == [(1, 3), (2, 3), (3, 3)]


class TestCancelling:

    def _blocking_work(self, started: threading.Event):
        def work(progress):
            started.set()

            for done in range(10_000):
                progress.step(done, 10_000)

            return "finished"

        return work

    def test_a_cancelled_job_reports_cancellation_not_a_result(self, runner, qt_app):
        started, outcome = threading.Event(), []

        handle = runner.run(
            self._blocking_work(started),
            lambda result: outcome.append(("done", result)),
            on_cancelled=lambda: outcome.append(("cancelled",)),
        )
        started.wait(5)
        handle.cancel()
        _settle(runner, qt_app)

        assert outcome == [("cancelled",)]

    def test_cancelling_is_not_an_error(self, runner, qt_app):
        started, errors = threading.Event(), []

        handle = runner.run(
            self._blocking_work(started), lambda _result: None, errors.append,
            on_cancelled=lambda: None,
        )
        started.wait(5)
        handle.cancel()
        _settle(runner, qt_app)

        assert errors == []

    def test_the_handle_knows_it_was_cancelled(self, runner, qt_app):
        started = threading.Event()
        handle = runner.run(
            self._blocking_work(started), lambda _r: None, on_cancelled=lambda: None,
        )
        started.wait(5)

        handle.cancel()

        assert handle.is_cancelled is True
        _settle(runner, qt_app)

    def test_a_job_left_alone_still_finishes(self, runner, qt_app):
        results = []

        runner.run(lambda p: (p.step(1, 1), "finished")[1], results.append)
        _settle(runner, qt_app)

        assert results == ["finished"]
