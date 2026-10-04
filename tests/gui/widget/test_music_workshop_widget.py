# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

INSTRUMENTS = 6
PERCUSSIONS = 4
UNITY = 4096


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _song(instrument_pitch: int = UNITY) -> bytes:
    return build_cseq_bytes(
        instruments=[
            CseqInstrument(sample_id=i % 2, frequency=instrument_pitch, volume=200)
            for i in range(INSTRUMENTS)
        ],
        percussions=[
            CseqPercussion(sample_id=i % 2, frequency=UNITY) for i in range(PERCUSSIONS)
        ],
    )


@pytest.fixture
def window(app):
    window = MainWindow(container)
    window.hwl = HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2) for _ in range(4)],
        banks=[build_bank_blob([0, 1], [b"\x00" * 16, b"\x00" * 16])],
        songs=[_song(), _song(), _song()],
    )
    window._rebuild_tree()
    return window


@pytest.fixture
def workshop(window):
    return window.music_workshop


def _settle() -> None:
    """Flush the widgets a re-render dropped.

    `deleteLater` posts a DeferredDelete event, and `processEvents` does not
    deliver those outside a running event loop — so without this the dead
    tables are still children and a test reads stale text from one of them.
    """
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def _tables(workshop) -> list[QTableWidget]:
    _settle()
    return workshop._detail_inner.findChildren(QTableWidget)


def _table_with(workshop, *headers: str) -> QTableWidget:
    for table in _tables(workshop):
        labels = {
            table.horizontalHeaderItem(c).text()
            for c in range(table.columnCount())
            if table.horizontalHeaderItem(c) is not None
        }
        if set(headers) <= labels:
            return table

    raise AssertionError(f"no table with headers {headers}")


def instruments_table(workshop) -> QTableWidget:
    return _table_with(workshop, "Volume", "ADSR")


def percussion_table(workshop) -> QTableWidget:
    return _table_with(workshop, "Drum name")


def _column(table: QTableWidget, header: str) -> int:
    for c in range(table.columnCount()):
        item = table.horizontalHeaderItem(c)
        if item is not None and item.text() == header:
            return c

    raise AssertionError(f"no {header!r} column")


class TestSongList:

    def test_lists_every_song(self, workshop):
        assert workshop._song_list.count() == 3

    def test_rows_carry_their_song_index(self, workshop):
        indices = [
            workshop._song_list.item(row).data(Qt.UserRole)
            for row in range(workshop._song_list.count())
        ]

        assert indices == [0, 1, 2]

    def test_selecting_a_song_renders_its_detail(self, workshop):
        workshop._song_list.setCurrentRow(1)

        assert instruments_table(workshop).rowCount() == INSTRUMENTS


class TestDetailTables:

    def test_one_row_per_instrument(self, workshop):
        workshop._song_list.setCurrentRow(0)

        assert instruments_table(workshop).rowCount() == INSTRUMENTS

    def test_one_row_per_percussion(self, workshop):
        workshop._song_list.setCurrentRow(0)

        assert percussion_table(workshop).rowCount() == PERCUSSIONS

    def test_instrument_rows_show_their_volume(self, workshop):
        workshop._song_list.setCurrentRow(0)
        table = instruments_table(workshop)

        assert table.item(0, _column(table, "Volume")).text() == "200/255"

    def test_instrument_rows_show_a_pitch_in_hz(self, workshop):
        workshop._song_list.setCurrentRow(0)
        table = instruments_table(workshop)

        assert "Hz" in table.item(0, _column(table, "Pitch")).text()


class TestWhatSurvivesTheFileChanging:
    """The user's place in the file. A refresh is triggered by every edit, so
    anything lost here is lost on every action."""

    def test_the_selected_song_is_kept(self, window, workshop):
        workshop._song_list.setCurrentRow(2)

        window.music_workshop.refresh(window.hwl, None)

        assert workshop._song_list.currentRow() == 2

    def test_a_song_beyond_the_new_end_falls_back_to_the_first(self, window, workshop):
        workshop._song_list.setCurrentRow(2)
        del window.hwl.songs[1:]

        window.music_workshop.refresh(window.hwl, None)

        assert workshop._song_list.currentRow() == 0

    def test_an_edited_pitch_reaches_the_table(self, window, workshop):
        workshop._song_list.setCurrentRow(0)
        table = instruments_table(workshop)
        pitch_column = _column(table, "Pitch")
        before = table.item(0, pitch_column).text()

        window.hwl.songs[0] = _song(instrument_pitch=2 * UNITY)
        window.music_workshop.refresh(window.hwl, None)

        after = instruments_table(workshop).item(0, pitch_column).text()
        assert after != before


class TestClosingTheFile:

    def test_closing_empties_the_song_list(self, window, workshop):
        """It used to keep listing the closed file's songs."""
        workshop._song_list.setCurrentRow(1)

        window.music_workshop.refresh(None)

        assert workshop._song_list.count() == 0
