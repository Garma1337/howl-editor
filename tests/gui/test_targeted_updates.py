# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.ctr.formats.howl.models import HowlFile, OtherFX, SpuAddrEntry
from howl_editor.gui.howl_change import HowlChange
from howl_editor.gui.main_window import MainWindow, NODE_SONG
from howl_editor.gui.widget.notification_bar import SUCCESS, WARNING
from howl_editor.ps1 import spu
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

UNITY = 4096
INSTRUMENTS = 8


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _settle() -> None:
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def _song(pitch: int = UNITY, instruments: int = INSTRUMENTS) -> bytes:
    return build_cseq_bytes(
        instruments=[
            CseqInstrument(sample_id=i % 2, frequency=pitch, volume=200)
            for i in range(instruments)
        ],
        percussions=[CseqPercussion(sample_id=0, frequency=UNITY) for _ in range(3)],
    )


@pytest.fixture
def window(app):
    window = MainWindow(container)
    window.hwl = HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2) for _ in range(4)],
        other_fx=[OtherFX(1, 128, 4096, 0, 100)],
        banks=[build_bank_blob([0, 1], [b"\x00" * 16] * 2) for _ in range(3)],
        songs=[_song(), _song(), _song()],
    )
    window._rebuild_tree()
    return window


def _instrument_table(window) -> QTableWidget:
    _settle()

    for table in window.music_workshop._detail_inner.findChildren(QTableWidget):
        labels = {
            table.horizontalHeaderItem(c).text()
            for c in range(table.columnCount())
            if table.horizontalHeaderItem(c) is not None
        }
        if "ADSR" in labels:
            return table

    raise AssertionError("no instruments table")


def _mark(table, rows) -> None:
    table.clearSelection()

    for row in rows:
        for col in range(table.columnCount() - 1):
            item = table.item(row, col)

            if item is not None:
                item.setSelected(True)


def _marked(table) -> list[int]:
    return sorted({index.row() for index in table.selectedIndexes()})


def _song_change(index: int) -> HowlChange:
    return HowlChange(collection=HowlCollection.SONGS, index=index)


class TestWorkshopKeepsTheUsersPlace:

    def test_marked_rows_survive_an_edit_to_the_song(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        table = _instrument_table(window)
        _mark(table, (2, 3, 4))

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert _marked(_instrument_table(window)) == [2, 3, 4]

    def test_the_table_is_the_same_widget_afterwards(self, window):
        """The proof that nothing was rebuilt: the rows the user marked are the
        same objects, not new ones that happen to look alike."""
        window.music_workshop._song_list.setCurrentRow(1)
        table = _instrument_table(window)

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert _instrument_table(window) is table

    def test_the_edited_value_reaches_the_row(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        before = _instrument_table(window).item(0, 3).text()

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert _instrument_table(window).item(0, 3).text() != before

    def test_an_edit_to_another_song_leaves_the_rendered_one_alone(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        table = _instrument_table(window)
        _mark(table, (5,))

        window.hwl.songs[0] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(0))

        assert _instrument_table(window) is table
        assert _marked(_instrument_table(window)) == [5]

    def test_a_bank_edit_leaves_the_rendered_song_alone(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        table = _instrument_table(window)

        window.apply_change(HowlChange(collection=HowlCollection.BANKS, index=2))

        assert _instrument_table(window) is table

    def test_a_structural_change_rebuilds_so_the_new_rows_appear(self, window):
        window.music_workshop._song_list.setCurrentRow(1)

        window.hwl.songs[1] = _song(instruments=INSTRUMENTS + 2)
        window.apply_change(_song_change(1))

        assert _instrument_table(window).rowCount() == INSTRUMENTS + 2


class TestAddingRowsKeepsThePanel:
    """Adding an instrument changes a row count, so that section has to be
    built again - the row actions capture their index. Only that section."""

    def _percussion_table(self, window):
        _settle()

        for table in window.music_workshop._detail_inner.findChildren(QTableWidget):
            labels = {
                table.horizontalHeaderItem(c).text()
                for c in range(table.columnCount())
                if table.horizontalHeaderItem(c) is not None
            }
            if "Drum name" in labels:
                return table

        raise AssertionError("no percussion table")

    def test_the_untouched_sections_are_the_same_widgets(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        percussion = self._percussion_table(window)

        window.hwl.songs[1] = _song(instruments=INSTRUMENTS + 1)
        window.apply_change(_song_change(1))

        assert self._percussion_table(window) is percussion

    def test_the_grown_section_shows_the_new_row(self, window):
        window.music_workshop._song_list.setCurrentRow(1)

        window.hwl.songs[1] = _song(instruments=INSTRUMENTS + 1)
        window.apply_change(_song_change(1))

        assert _instrument_table(window).rowCount() == INSTRUMENTS + 1

    def test_marks_that_still_fit_are_re_applied(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        _mark(_instrument_table(window), (2, 3))

        window.hwl.songs[1] = _song(instruments=INSTRUMENTS + 1)
        window.apply_change(_song_change(1))

        assert _marked(_instrument_table(window)) == [2, 3]

    def test_the_stats_strip_follows_the_new_count(self, window):
        from PySide6.QtWidgets import QLabel

        window.music_workshop._song_list.setCurrentRow(1)

        window.hwl.songs[1] = _song(instruments=INSTRUMENTS + 1)
        window.apply_change(_song_change(1))
        _settle()

        texts = [
            label.text()
            for label in window.music_workshop._stats_bar.findChildren(QLabel)
        ]
        assert str(INSTRUMENTS + 1) in texts


class TestFileBrowserKeepsItsState:

    def _song_node(self, window, index):
        return window._nodes[(NODE_SONG, index, None)]

    def test_an_expanded_node_stays_expanded(self, window):
        node = self._song_node(window, 1)
        node.setExpanded(True)

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert self._song_node(window, 1).isExpanded()

    def test_the_selected_item_stays_selected(self, window):
        node = self._song_node(window, 1)
        window.tree.setCurrentItem(node)

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert window.tree.currentItem() is node

    def test_the_detail_panel_keeps_showing_the_selection(self, window):
        """It used to be cleared on every edit, leaving a blank pane next to a
        still-selected song."""
        window.tree.setCurrentItem(self._song_node(window, 1))
        assert window.details.toPlainText().strip()

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert window.details.toPlainText().strip()

    def test_an_edited_songs_children_are_rebuilt_when_open(self, window):
        node = self._song_node(window, 1)
        node.setExpanded(True)
        window._ensure_children(node)
        before = node.childCount()

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert self._song_node(window, 1).childCount() == before

    def test_an_unopened_songs_children_are_left_deferred(self, window):
        """Rebuilding them would undo the laziness that keeps a stock file's
        ~4000 rows out of the tree."""
        window.hwl.songs[2] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(2))

        assert self._song_node(window, 2).childCount() == 0


class TestCategoryBrowserKeepsItsPlace:

    def test_an_open_category_is_not_re_rendered(self, window):
        tab = window.main_tab
        group = max(tab._groups, key=lambda g: len(g.rows))
        tab._on_category_clicked(group)
        _settle()
        rows = tab._detail._row_widgets()

        window.hwl.songs[0] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(0))
        _settle()

        assert tab._detail._row_widgets() == rows

    def test_the_cards_are_not_rebuilt(self, window):
        tab = window.main_tab
        cards = dict(tab._grid._cards)

        window.hwl.songs[0] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(0))

        assert tab._grid._cards == cards


class TestBatching:
    """Replacing a sample several banks share pushes one command per bank."""

    def test_changes_inside_a_batch_apply_once(self, window):
        applied = []
        window.music_workshop.apply_change = lambda *args: applied.append(args[-1])

        with window.batched_changes():
            window.apply_change(HowlChange(HowlCollection.BANKS, 0))
            window.apply_change(HowlChange(HowlCollection.BANKS, 1))
            window.apply_change(HowlChange(HowlCollection.BANKS, 2))

        assert len(applied) == 1

    def test_the_merged_change_still_covers_every_bank(self, window):
        applied = []
        window.music_workshop.apply_change = lambda *args: applied.append(args[-1])

        with window.batched_changes():
            window.apply_change(HowlChange(HowlCollection.BANKS, 0))
            window.apply_change(HowlChange(HowlCollection.BANKS, 2))

        assert applied[0].touches(HowlCollection.BANKS, 0)
        assert applied[0].touches(HowlCollection.BANKS, 2)


class TestRowActionsFollowTheDescriptor:
    """The buttons in a row used to close over the sample and pitch they were
    built with, so after an edit the Play button auditioned the previous
    sample and Replace overwrote the previous bank slot. They resolve the
    descriptor when pressed instead."""

    def _play_button(self, window, row: int):
        from PySide6.QtWidgets import QPushButton

        cell = _instrument_table(window).cellWidget(row, 6)

        return next(
            b for b in cell.findChildren(QPushButton) if b.text() == "\u25b6\ufe0f"
        )

    def test_play_auditions_the_pitch_the_row_shows_now(self, window):
        window.music_workshop._song_list.setCurrentRow(1)
        heard = []
        window.music_workshop.sig_play_instrument.connect(
            lambda spu, pitch, label: heard.append((spu, pitch)),
        )

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))
        self._play_button(window, 0).click()

        assert heard[-1][1] == 2 * UNITY

    def test_play_auditions_the_sample_the_row_points_at_now(self, window):
        """A retarget changes the descriptor's sample id without changing how
        many descriptors there are."""
        window.music_workshop._song_list.setCurrentRow(1)
        heard = []
        window.music_workshop.sig_play_instrument.connect(
            lambda spu, pitch, label: heard.append((spu, pitch)),
        )

        retargeted = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=1, frequency=UNITY, volume=200)]
            + [
                CseqInstrument(sample_id=i % 2, frequency=UNITY, volume=200)
                for i in range(1, INSTRUMENTS)
            ],
            percussions=[CseqPercussion(sample_id=0, frequency=UNITY) for _ in range(3)],
        )
        window.hwl.songs[1] = retargeted
        window.apply_change(_song_change(1))
        self._play_button(window, 0).click()

        assert heard[-1][0] == 1

    def test_the_action_widget_is_not_replaced_on_an_ordinary_edit(self, window):
        """Rebuilding ~60 of these per edit cost more than the whole targeted
        update does."""
        window.music_workshop._song_list.setCurrentRow(1)
        cell = _instrument_table(window).cellWidget(0, 6)

        window.hwl.songs[1] = _song(pitch=2 * UNITY)
        window.apply_change(_song_change(1))

        assert _instrument_table(window).cellWidget(0, 6) is cell


class TestShiftReporting:

    def _severities(self, window) -> list[str]:
        return [row.property("severity") for row in window.notifications._rows]

    def test_a_shift_that_moved_nothing_warns(self, window):
        at_ceiling = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=0, frequency=spu.MAX_PITCH, volume=200)],
        )
        window.hwl.songs[1] = at_ceiling
        window.notifications.clear()

        window._song_handler.shift_instrument_octaves(1, 0, 1)

        assert self._severities(window) == [WARNING]
        assert "4.0" in window.notifications.messages()[0]

    def test_a_shift_that_moved_something_confirms(self, window):
        window.notifications.clear()

        window._song_handler.shift_instrument_octaves(1, 0, 1)

        assert self._severities(window) == [SUCCESS]
