# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel, QRadioButton

from howl_editor.ctr.analysis.sample_replacement_planner import SampleReplacementPlan
from howl_editor.ctr.diagnostics.bank_size_guard import BankSizeCheck
from howl_editor.ctr.diagnostics.shared_sample_guard import BankImpact
from howl_editor.gui.dialog.replace_sample_dialog import ReplaceSampleDialog
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _plan(shared=(), over_limit=False, new_size=4096) -> SampleReplacementPlan:
    impacts = [
        BankImpact(bank_index=i, bank_name=f"Bank {i}", bad_slices=1, sample_count=4)
        for i in shared
    ]
    size = BankSizeCheck(
        within_limit=not over_limit, total_bytes=1, ceiling=1, over_by=1 if over_limit else 0,
        resident_banks=(), warning_text="Bank 15 would overrun SPU RAM" if over_limit else "",
    )

    return SampleReplacementPlan(
        bank_index=15, sample_index=45, spu_index=404,
        old_byte_size=3088, new_byte_size=new_size, new_blob=b"",
        shared_impacts=impacts, bank_size=size,
    )


def _dialog(qt_app, plan) -> ReplaceSampleDialog:
    return ReplaceSampleDialog(None, plan, "new_drum.vag", "Bank 15 — Coco Park")


def _texts(dialog) -> str:
    """Everything the dialog says, so a test can assert on what is on screen."""
    widgets = dialog.findChildren(QLabel) + dialog.findChildren(QRadioButton)
    return " ".join(widget.text() for widget in widgets)


class TestSharedDecision:

    def test_no_choice_offered_when_nothing_else_holds_the_slot(self, qt_app):
        dialog = _dialog(qt_app, _plan())

        assert dialog.findChildren(QRadioButton) == []
        assert dialog.chosen().update_shared_banks is False

    def test_updating_the_other_banks_is_the_default(self, qt_app):
        dialog = _dialog(qt_app, _plan(shared=(6,)))

        assert dialog.chosen().update_shared_banks is True

    def test_choosing_this_bank_only_is_reported(self, qt_app):
        dialog = _dialog(qt_app, _plan(shared=(6,)))

        dialog.findChildren(QRadioButton)[1].setChecked(True)

        assert dialog.chosen().update_shared_banks is False

    def test_one_other_bank_reads_as_singular(self, qt_app):
        dialog = _dialog(qt_app, _plan(shared=(6,)))

        assert "Update that bank as well (recommended)" in _texts(dialog)

    def test_several_other_banks_read_as_plural(self, qt_app):
        dialog = _dialog(qt_app, _plan(shared=(6, 9)))

        assert "Update those banks as well (recommended)" in _texts(dialog)


class TestFacts:

    def test_a_larger_sample_states_both_sizes(self, qt_app):
        dialog = _dialog(qt_app, _plan())

        assert "1008 bytes larger" in _texts(dialog)
        assert "3088 → 4096 bytes" in _texts(dialog)

    def test_a_same_size_replacement_says_nothing_else_is_affected(self, qt_app):
        dialog = _dialog(qt_app, _plan(new_size=3088))

        assert "no other bank is affected" in _texts(dialog)

    def test_an_over_budget_result_is_shown_up_front(self, qt_app):
        dialog = _dialog(qt_app, _plan(over_limit=True))

        assert "would overrun SPU RAM" in _texts(dialog)

    def test_the_budget_line_is_absent_when_it_fits(self, qt_app):
        dialog = _dialog(qt_app, _plan())

        assert "overrun" not in _texts(dialog)


class TestSaphiCap:

    def _plan_with_blob(self, blob_bytes: int):
        plan = _plan()
        return SampleReplacementPlan(**{**plan.__dict__, "new_blob": b"\x00" * blob_bytes})

    def test_a_bank_over_saphi_s_cap_is_called_out(self, qt_app):
        dialog = _dialog(qt_app, self._plan_with_blob(SAPHI_BANK_MAX_SIZE + 2048))

        assert "over Saphi's" in _texts(dialog)

    def test_a_bank_within_the_cap_says_nothing(self, qt_app):
        dialog = _dialog(qt_app, self._plan_with_blob(1024))

        assert "Saphi" not in _texts(dialog)
