# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.widget.notification_bar import (
    DANGER, INFO, MAX_VISIBLE, SUCCESS, WARNING, NotificationBar,
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
