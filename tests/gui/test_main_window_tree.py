# coding: utf-8

"""Bank samples and song sequences are built only when a node is opened.

A stock file has ~4000 of those rows, and rebuilding them after every edit is
what made the tree slow. Anything that reads the tree — expanding, restoring
the previous expansion, filtering — has to pull them in first.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QStatusBar

from types import SimpleNamespace

from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.gui.main_window import MainWindow
from howl_editor.gui.widget.notification_bar import DANGER, INFO, SUCCESS, WARNING
from howl_editor.core import Container
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    window = MainWindow(container)
    window.hwl = HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2) for _ in range(4)],
        banks=[build_bank_blob([0, 3], [b"\x00" * 16, b"\x00" * 16])],
        songs=[build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])],
    )
    window._rebuild_tree()
    return window


def _node(window, label_prefix: str):
    root = window.tree.topLevelItem(0)

    for i in range(root.childCount()):
        group = root.child(i)
        # The row may carry a diagnosis badge ("❌ Banks").
        if label_prefix in group.text(0):
            return group.child(0)

    raise AssertionError(f"no {label_prefix} node")


class TestDeferredChildren:

    def test_bank_samples_are_not_built_up_front(self, window):
        assert _node(window, "Banks").childCount() == 0

    def test_expanding_a_bank_builds_its_samples(self, window):
        bank = _node(window, "Banks")

        bank.setExpanded(True)

        assert [bank.child(i).text(0) for i in range(bank.childCount())] == ["SPU 0", "SPU 3"]

    def test_expanding_a_song_builds_its_sequences(self, window):
        song = _node(window, "Songs")

        song.setExpanded(True)

        assert song.childCount() == 1

    def test_children_are_built_once(self, window):
        bank = _node(window, "Banks")

        bank.setExpanded(True)
        bank.setExpanded(False)
        bank.setExpanded(True)

        assert bank.childCount() == 2


class TestStateAcrossRebuilds:

    def test_an_expanded_bank_comes_back_populated(self, window):
        _node(window, "Banks").setExpanded(True)

        window._rebuild_tree()

        bank = _node(window, "Banks")
        assert bank.isExpanded()
        assert bank.childCount() == 2


class TestFiltering:

    def test_a_sample_inside_a_collapsed_bank_is_still_found(self, window):
        window.filter_widget._input.setText("SPU 3")

        bank = _node(window, "Banks")
        matches = [
            bank.child(i).text(0) for i in range(bank.childCount())
            if not bank.child(i).isHidden()
        ]

        assert matches == ["SPU 3"]

    def test_clearing_the_filter_unhides_everything(self, window):
        window.filter_widget._input.setText("SPU 3")
        window.filter_widget._input.setText("")

        bank = _node(window, "Banks")
        assert not any(bank.child(i).isHidden() for i in range(bank.childCount()))


class TestNotifying:
    """Every report goes to the notification bar; the window has no status bar
    behind it any more.
    """

    @pytest.mark.parametrize("notify, severity", [
        ("_notify", SUCCESS),
        ("_notify_info", INFO),
        ("_notify_warning", WARNING),
        ("_notify_danger", DANGER),
    ])
    def test_each_level_reaches_the_bar(self, window, notify, severity):
        getattr(window, notify)("something happened")

        assert window.notifications.messages() == ["something happened"]
        assert window.notifications._rows[0].property("severity") == severity

    def test_the_window_has_no_status_bar(self, window):
        # statusBar() would create one on demand, so ask without conjuring it.
        assert window.findChild(QStatusBar) is None


class TestLazyAudioPlayer:
    """Building the player pulls in Qt's multimedia stack (~6 MB measured), so
    it waits for the first sound rather than loading with the window.
    """

    def _window_with_fake_player(self, app, calls):
        # media_player None stands for "QtMultimedia missing", so the window
        # skips connecting the transport widgets to it.
        player = SimpleNamespace(media_player=None, available=False)
        services = Container()

        for name, factory in container._factories.items():
            services.register(name, factory)

        services.register("audio_player", lambda c: calls.append(1) or player)

        return MainWindow(services), player

    def test_the_player_is_not_built_with_the_window(self, app):
        calls = []

        self._window_with_fake_player(app, calls)

        assert calls == []

    def test_the_first_request_builds_it(self, app):
        calls = []
        window, player = self._window_with_fake_player(app, calls)

        assert window.ensure_audio_player() is player
        assert calls == [1]

    def test_later_requests_reuse_it(self, app):
        calls = []
        window, _player = self._window_with_fake_player(app, calls)

        window.ensure_audio_player()
        window.ensure_audio_player()

        assert calls == [1]

    def test_playback_is_offered_before_the_player_exists(self, app):
        # can_play() is asked on every play; it must not be what builds it.
        calls = []
        window, _player = self._window_with_fake_player(app, calls)

        window._playback.can_play()

        assert calls == []
