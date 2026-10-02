# coding: utf-8

"""Which render gets to play.

A render takes seconds and lands long after the click that started it, so the
handler has to decide what a late result is still allowed to do.
"""

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.handler.playback_handler import PlaybackHandler
from howl_editor.gui.widget.notification_bar import NotificationBar


class FakeHandle:
    def __init__(self):
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeRunner:
    """Stands in for ProcessTaskRunner: records the job and lets a test
    deliver its result whenever it likes."""

    def __init__(self):
        self.jobs = []

    def run(self, func, args=(), kwargs=None, on_success=None, on_error=None,
            on_cancelled=None, on_progress=None):
        handle = FakeHandle()
        self.jobs.append(SimpleNamespace(handle=handle, deliver=on_success))

        return handle


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qt_app):
    """A stand-in for MainWindow: the handler reaches services through the
    container, so the fake serves the render runner from there."""
    runner = FakeRunner()
    services = SimpleNamespace(
        resolve=lambda name: runner if name == "process_tasks" else None,
        is_instantiated=lambda name: False,
    )

    return SimpleNamespace(
        hwl=SimpleNamespace(banks=[]),
        audio_player_if_built=None,
        _services=services,
        _render_runner=runner,
        notifications=NotificationBar(dismiss_ms=10_000),
        player_widgets=[],
        waveforms=[],
    )


@pytest.fixture
def handler(window):
    return PlaybackHandler(window)


@pytest.fixture
def played(handler, monkeypatch):
    played = []
    monkeypatch.setattr(handler, "_play_wav", lambda wav, label, *a, **k: played.append(label))
    monkeypatch.setattr(handler, "_store_wav", lambda *a, **k: None)

    return played


def _start(handler, label: str) -> None:
    handler._render_then_play(b"song", 0, None, label, lambda: ("args",), None)


class TestSupersededRenders:

    def test_the_result_plays_when_it_is_still_the_current_render(self, handler, window, played):
        _start(handler, "Song A")

        window._render_runner.jobs[0].deliver(b"wav")

        assert played == ["Song A"]

    def test_starting_another_render_cancels_the_first(self, handler, window, played):
        _start(handler, "Song A")
        _start(handler, "Song B")

        assert window._render_runner.jobs[0].handle.cancelled is True

    def test_a_superseded_result_does_not_play_over_the_new_one(self, handler, window, played):
        _start(handler, "Song A")
        _start(handler, "Song B")

        window._render_runner.jobs[1].deliver(b"wav-b")
        window._render_runner.jobs[0].deliver(b"wav-a")   # the old mix lands late

        assert played == ["Song B"]


class TestStopping:

    def test_stop_abandons_a_render_in_flight(self, handler, window, played):
        _start(handler, "Song A")

        handler.stop()

        assert window._render_runner.jobs[0].handle.cancelled is True

    def test_a_render_abandoned_by_stop_never_plays(self, handler, window, played):
        _start(handler, "Song A")
        handler.stop()

        window._render_runner.jobs[0].deliver(b"wav")

        assert played == []
