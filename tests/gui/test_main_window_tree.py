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

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

_ALIASES = {"howl_editor_svc": "howl_editor", "drum_names": "gm_drum_names"}

_PARAMS = [
    "howl_reader", "cseq_reader", "cseq_parses", "bank_reader", "sample_lookup",
    "sample_classifier", "detail_formatter", "stylesheet_loader", "drum_names",
    "size_formatter", "severity_presenter", "entry_badge_resolver", "stock_layout",
    "semantic_entry_builder", "entry_leaves_builder", "category_icon_resolver",
    "leaf_info_formatter", "howl_stats_calculator", "adventure_hub_mask_table_query",
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    kwargs = {p: container.resolve(_ALIASES.get(p, p)) for p in _PARAMS}
    window = MainWindow(**kwargs)
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
        if group.text(0).startswith(label_prefix):
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
