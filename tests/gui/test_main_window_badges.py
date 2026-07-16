# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from howl_editor.ctr import constants
from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.services import container
from tests.conftest import build_cseq_bytes

# Constructor param name -> container service name (only where they differ).
_ALIASES = {"howl_editor_svc": "howl_editor", "drum_names": "gm_drum_names"}

_PARAMS = [
    "howl_reader", "howl_writer", "howl_editor_svc", "cseq_reader", "cseq_writer",
    "cseq_editor", "vag_reader", "vag_writer", "bank_reader", "bank_builder",
    "midi_converter", "midi_exporter", "vag_decoder", "cseq_renderer", "audio_player",
    "resampler", "wav_writer", "vag_rate_provider", "audio_cache", "sample_lookup",
    "version_detector", "sample_classifier", "validator", "batch_exporter",
    "sfz_exporter", "detail_formatter", "sca_reader", "sca_writer",
    "sample_sizes_extractor", "semantic_entry_builder", "entry_leaves_builder",
    "blob_snapshot", "entry_drop_router", "stylesheet_loader",
    "adventure_hub_mask_table_query", "category_icon_resolver", "cseq_size_validator",
    "cseq_size_guard", "bank_size_guard", "howl_size_guard", "howl_diagnostics",
    "diagnostics_status_provider", "entry_badge_resolver", "severity_presenter",
    "diagnosis_banner_formatter", "drum_names", "stock_layout", "leaf_info_formatter",
    "howl_stats_calculator", "size_formatter",
]

from howl_editor.gui.main_window import MainWindow, NODE_SONG, NODE_ROOT


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    kwargs = {p: container.resolve(_ALIASES.get(p, p)) for p in _PARAMS}
    return MainWindow(**kwargs)


def _oversized_song() -> bytes:
    base = build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])
    return base + b"\x00" * (constants.MAX_CSEQ_BYTES + 2048 - len(base))


def _song_rows(window):
    def walk(item):
        yield item
        for i in range(item.childCount()):
            yield from walk(item.child(i))

    root = window.tree.topLevelItem(0)
    return {
        it.data(0, Qt.UserRole + 1): it.text(0)
        for it in walk(root)
        if it.data(0, Qt.UserRole) == NODE_SONG
    }


class TestTreeBadges:

    def test_oversized_song_row_gets_error_badge(self, window):
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.songs = [_oversized_song(), build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])]
        window.hwl = hwl
        window.file_path = None
        window._original_howl_size = None
        window._custom_mode = False

        window._rebuild_tree()
        rows = _song_rows(window)

        assert rows[0].startswith("❌")     # oversized song
        assert not rows[1].startswith("❌")  # in-limit song
        assert not rows[1].startswith("⚠️")

    def test_detail_banner_only_on_flagged_item(self, window):
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.songs = [_oversized_song(), build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])]
        window.hwl = hwl
        window.file_path = None
        window._original_howl_size = None
        window._custom_mode = False
        window._rebuild_tree()

        assert window._banner_html(NODE_SONG, 0) != ""      # flagged song shows a banner
        assert window._banner_html(NODE_SONG, 1) == ""      # clean song: none
        assert window._banner_html(NODE_ROOT, None) == ""   # file size fine: none

    def test_custom_mode_suppresses_badges_and_guards(self, window):
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.songs = [_oversized_song()]
        window.hwl = hwl
        window.file_path = None
        window._original_howl_size = None
        window._custom_mode = True

        window._rebuild_tree()

        # No badge on the oversized song, no banner, and the guard passes silently.
        assert not _song_rows(window)[0].startswith("❌")
        assert window._banner_html(NODE_SONG, 0) == ""

        class _OverCheck:
            within_limit = False
            warning_text = "nope"

        assert window.confirm_within_limit(_OverCheck()) is True
