# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel

from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.howl.models import HowlFile, OtherFX, SpuAddrEntry
from howl_editor.gui.main_window import MainWindow
from howl_editor.gui.widget.category_card_widget import CategoryCardWidget
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

PAGE_GRID = 1
PAGE_DETAIL = 2


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _settle() -> None:
    """See test_music_workshop_widget: deleteLater needs an explicit flush
    outside a running event loop."""
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


@pytest.fixture
def window(app):
    window = MainWindow(container)
    window.hwl = HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2) for _ in range(4)],
        other_fx=[OtherFX(1, 128, 4096, i % 2, 100) for i in range(5)],
        banks=[build_bank_blob([0, 1], [b"\x00" * 16] * 2) for _ in range(6)],
        songs=[
            build_cseq_bytes(instruments=[CseqInstrument(sample_id=0, frequency=4096)])
            for _ in range(6)
        ],
    )
    window._rebuild_tree()
    return window


@pytest.fixture
def tab(window):
    return window.main_tab


def _cards(tab) -> dict[str, CategoryCardWidget]:
    _settle()
    return {card._group.name: card for card in tab._grid.findChildren(CategoryCardWidget)}


def _card_text(card) -> str:
    return " | ".join(
        label.text() for label in card.findChildren(QLabel) if label.text()
    )


def _biggest_group(tab):
    return max(tab._groups, key=lambda g: len(g.rows))


class TestGrid:

    def test_opens_on_the_card_grid(self, tab):
        assert tab._stack.currentIndex() == PAGE_GRID

    def test_builds_a_card_per_category(self, tab):
        assert set(_cards(tab)) == {group.name for group in tab._groups}

    def test_a_card_reports_how_many_entries_its_category_holds(self, tab):
        group = _biggest_group(tab)

        assert str(len(group.rows)) in _card_text(_cards(tab)[group.name])


class TestDrillDown:

    def test_clicking_a_category_opens_its_page(self, tab):
        group = _biggest_group(tab)

        tab._on_category_clicked(group)

        assert tab._stack.currentIndex() == PAGE_DETAIL
        assert tab._detail._title.text() == group.name

    def test_the_page_lists_the_category_entries(self, tab):
        from howl_editor.gui.widget.entry_parent_widget import EntryParentWidget
        from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget

        group = _biggest_group(tab)
        tab._on_category_clicked(group)
        _settle()

        rows = tab._detail.findChildren(EntryParentWidget) + [
            w for w in tab._detail.findChildren(LeafRowWidget)
            if w.parent() is tab._detail._scroll_inner
        ]
        assert len(rows) == len(group.rows)


class TestWhatSurvivesTheFileChanging:

    def test_the_grid_stays_on_the_grid(self, window, tab):
        window.main_tab.refresh(window.hwl, None)

        assert tab._stack.currentIndex() == PAGE_GRID

    def test_an_open_category_stays_open(self, window, tab):
        group = _biggest_group(tab)
        tab._on_category_clicked(group)

        window.main_tab.refresh(window.hwl, None)

        assert tab._stack.currentIndex() == PAGE_DETAIL
        assert tab._detail._title.text() == group.name

    def test_a_removed_category_falls_back_to_the_grid(self, window, tab):
        group = _biggest_group(tab)
        tab._on_category_clicked(group)
        del window.hwl.banks[:]
        del window.hwl.songs[:]
        del window.hwl.other_fx[:]

        window.main_tab.refresh(window.hwl, None)

        assert tab._stack.currentIndex() != PAGE_DETAIL
