# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from howl_editor.gui.dialog.select_sample_dialog import (
    SampleChoice, SelectSampleDialog,
)


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _choices() -> list[SampleChoice]:
    return [
        SampleChoice(spu_index=3, display="SPU #3"),
        SampleChoice(spu_index=7, display="SPU #7"),
    ]


class TestPreview:

    def test_no_preview_button_without_callback(self, qt_app):
        dlg = SelectSampleDialog(None, "t", "p", _choices())

        assert not hasattr(dlg, "_preview_button")

    def test_preview_button_present_with_callback(self, qt_app):
        dlg = SelectSampleDialog(None, "t", "p", _choices(), on_preview=lambda _spu: None)

        assert dlg._preview_button is not None

    def test_preview_plays_the_selected_sample(self, qt_app):
        played: list[int] = []
        dlg = SelectSampleDialog(
            None, "t", "p", _choices(),
            current_spu_index=7, on_preview=played.append,
        )

        dlg._preview_selected()

        assert played == [7]

    def test_preview_noop_when_nothing_selected(self, qt_app):
        played: list[int] = []
        dlg = SelectSampleDialog(
            None, "t", "p", _choices(), on_preview=played.append,
        )
        dlg._list.setCurrentItem(None)

        dlg._preview_selected()

        assert played == []


class TestFreeAndDisabledRows:

    def test_free_slots_are_marked_in_the_list(self, qt_app):
        dlg = SelectSampleDialog(None, "t", "p", [
            SampleChoice(spu_index=3, display="SPU #3", free=True),
            SampleChoice(spu_index=7, display="SPU #7"),
        ])

        assert "free" in dlg._list.item(0).text()
        assert "free" not in dlg._list.item(1).text()

    def test_filtering_by_free_shows_only_free_slots(self, qt_app):
        dlg = SelectSampleDialog(None, "t", "p", [
            SampleChoice(spu_index=3, display="SPU #3", free=True),
            SampleChoice(spu_index=7, display="SPU #7"),
        ])

        dlg._apply_filter("free")

        assert [dlg._list.item(r).isHidden() for r in range(2)] == [False, True]

    def test_disabled_rows_cannot_be_selected(self, qt_app):
        dlg = SelectSampleDialog(None, "t", "p", [
            SampleChoice(spu_index=3, display="SPU #3", enabled=False),
        ])

        assert not dlg._list.item(0).flags() & Qt.ItemIsSelectable

    def test_current_skips_a_disabled_row_with_the_same_slot(self, qt_app):
        # The share row and the (disabled) table row carry the same slot.
        dlg = SelectSampleDialog(None, "t", "p", [
            SampleChoice(spu_index=3, display="SPU #3", enabled=False),
            SampleChoice(spu_index=3, display="share SPU #3"),
        ], current_spu_index=3)

        assert dlg._list.currentRow() == 1
        assert dlg.chosen_spu_index() == 3
