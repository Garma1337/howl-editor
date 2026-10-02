# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton

from howl_editor.gui.widget.notification_bar import (
    BUSY, DANGER, INFO, MAX_VISIBLE, SUCCESS, WARNING, NotificationBar,
)


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def bar(qt_app):
    # No auto-dismiss: the timer would need a running event loop to fire.
    return NotificationBar(dismiss_ms=10_000)


def _severities(bar) -> list[str]:
    return [row.property("severity") for row in bar._rows]


class TestPushing:

    def test_hidden_until_something_is_pushed(self, bar):
        assert bar.isVisible() is False

    def test_a_message_appears(self, bar):
        bar.push("Shifted 10 pitches up an octave")

        assert bar.messages() == ["Shifted 10 pitches up an octave"]

    @pytest.mark.parametrize("push, expected", [
        (lambda bar: bar.push("m"), INFO),
        (lambda bar: bar.push_success("m"), SUCCESS),
        (lambda bar: bar.push_warning("m"), WARNING),
        (lambda bar: bar.push_danger("m"), DANGER),
    ])
    def test_severity_is_carried_to_the_row(self, bar, push, expected):
        push(bar)

        assert _severities(bar) == [expected]

    def test_newest_message_is_last(self, bar):
        bar.push("first")
        bar.push("second")

        assert bar.messages() == ["first", "second"]


class TestCrowding:

    def test_only_the_most_recent_are_kept(self, bar):
        for i in range(MAX_VISIBLE + 2):
            bar.push(f"message {i}")

        assert bar.messages() == [f"message {i}" for i in range(2, MAX_VISIBLE + 2)]


class TestDismissing:

    def test_closing_the_last_one_hides_the_bar(self, bar):
        bar.push("done")

        bar._dismiss(bar._rows[0])

        assert bar.messages() == []
        assert bar.isVisible() is False

    def test_clear_removes_everything(self, bar):
        bar.push_warning("careful")
        bar.push_danger("stop")

        bar.clear()

        assert bar.messages() == []


class TestBusyRow:
    """A running job owns a row until it reports back."""

    def test_a_busy_row_shows_the_work(self, bar):
        bar.push_busy("Rendering Song 14…")

        assert bar.messages() == ["Rendering Song 14…"]
        assert _severities(bar) == [BUSY]

    def test_success_replaces_the_busy_row(self, bar):
        busy = bar.push_busy("Rendering Song 14…")

        busy.succeeded("Playing Song 14")

        assert bar.messages() == ["Playing Song 14"]
        assert _severities(bar) == [SUCCESS]

    def test_failure_replaces_the_busy_row(self, bar):
        busy = bar.push_busy("Exporting…")

        busy.failed("Batch export failed: disk full")

        assert _severities(bar) == [DANGER]

    def test_dismissing_leaves_nothing_behind(self, bar):
        busy = bar.push_busy("Rendering…")

        busy.dismiss()

        assert bar.messages() == []

    def test_a_running_job_is_never_crowded_out(self, bar):
        bar.push_busy("Rendering Song 14…")

        for i in range(MAX_VISIBLE + 2):
            bar.push(f"message {i}")

        assert "Rendering Song 14…" in bar.messages()


class TestStaleBusyHandle:
    """A job keeps reporting for a moment after its row is gone — cancelling
    races the updates already in flight. Touching the deleted widgets raised
    'Internal C++ object already deleted' once per update.
    """

    def test_progress_after_dismissal_is_ignored(self, bar):
        busy = bar.push_busy("Rendering…")
        busy.dismiss()

        busy.set_progress(500, 1000)

        assert bar.messages() == []

    def test_progress_after_the_outcome_is_ignored(self, bar):
        busy = bar.push_busy("Rendering…")
        busy.succeeded("Playing Song 14")

        busy.set_progress(500, 1000)

        assert bar.messages() == ["Playing Song 14"]

    def test_a_cancel_button_is_not_added_to_a_gone_row(self, bar):
        busy = bar.push_busy("Rendering…")
        busy.dismiss()

        busy.set_cancel(lambda: None)

    def test_a_running_row_has_no_dismiss_button(self, bar):
        # Closing it would delete the widgets the job still writes into.
        bar.push_busy("Rendering…")

        assert not bar._rows[0].findChildren(QPushButton)

    def test_finished_messages_keep_their_dismiss_button(self, bar):
        bar.push_success("Done")

        assert bar._rows[0].findChildren(QPushButton)
