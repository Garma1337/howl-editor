# coding: utf-8

from pathlib import Path

import pytest

from howl_editor.ctr.sample_lookup import SampleLookup
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.gui.detail.leaf_info_formatter import LeafInfoFormatter
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.gui.entries.entry_leaf import EntryLeaf, LeafKind
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.gui.entries.semantic_entry import EntryKind, EntryRow
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from tests.conftest import build_bank_blob


@pytest.fixture
def formatter():
    template_dir = Path(__file__).resolve().parent.parent.parent.parent / "howl_editor" / "gui" / "templates"
    bank_reader = BankReader(StockNameResolver())
    cseq_reader = CseqReader(VlqCodec(), StockNameResolver())
    sample_lookup = SampleLookup(bank_reader, cseq_reader)

    return LeafInfoFormatter(
        TemplateEngine(template_dir),
        bank_reader,
        cseq_reader,
        sample_lookup,
        SizeFormatter(),
    )


class TestSequenceLeaf:

    def test_renders_title_and_indices(self, formatter):
        leaf = EntryLeaf(
            kind=LeafKind.SEQUENCE, name="Main music", icon="🎵",
            song_index=8, seq_index=0,
        )

        html = formatter.format(leaf)

        assert "Main music" in html
        assert "Sequence" in html
        assert "Song slot" in html and ">8<" in html
        assert "Sub-song" in html and ">0<" in html

    def test_omits_missing_indices(self, formatter):
        leaf = EntryLeaf(kind=LeafKind.SEQUENCE, name="Boss Race", icon="🎵")

        html = formatter.format(leaf)

        assert "Sequence" in html
        assert "Song slot" not in html


class TestSampleLeaf:

    def test_renders_bank_sample_and_spu(self, formatter):
        leaf = EntryLeaf(
            kind=LeafKind.SAMPLE, name="Sample 3", icon="🔊",
            bank_index=5, sample_index=3, spu_index=42,
        )

        html = formatter.format(leaf)

        assert "Sample 3" in html
        assert "Bank slot" in html and ">5<" in html
        assert "SPU index" in html and ">42<" in html

    def test_includes_size_and_duration_when_hwl_provided(self, formatter):
        """Selecting a sample inside a category should show size + rough
        length, mirroring what File Content's sample details show."""
        sample_data = b"\x00" * 16 * 100  # 100 VAG blocks -> 2800 PCM samples
        spu_addrs = [SpuAddrEntry(0, 100)] * 5  # entry 0 covers the sample range
        bank_blob = build_bank_blob([0], [sample_data])
        hwl = HowlFile(spu_addrs=spu_addrs, banks=[bank_blob])

        leaf = EntryLeaf(
            kind=LeafKind.SAMPLE, name="Sample 0", icon="🔊",
            bank_index=0, sample_index=0, spu_index=0,
        )

        html = formatter.format(leaf, hwl)

        assert "Size" in html
        # 2800 PCM samples / 11025 Hz default ≈ 0.25 s — anyway, "ms" or "s"
        # must appear so the user sees some duration readout.
        assert "ms" in html or "s</td>" in html or " s<" in html


class TestEntrySelection:

    def test_bank_entry_shows_bank_size_and_sample_count(self, formatter):
        sample_data = b"\x00" * 32
        spu_addrs = [SpuAddrEntry(0, 32)]
        bank_blob = build_bank_blob([0], [sample_data])
        hwl = HowlFile(spu_addrs=spu_addrs, banks=[bank_blob])
        row = EntryRow(
            kind=EntryKind.BANK_ONLY, name="Crash Bandicoot",
            bank_index=0, accepts=(".bnk",),
        )

        html = formatter.format_entry(row, hwl)

        assert "Crash Bandicoot" in html
        assert "Bank slot" in html and ">0<" in html
        assert "Bank size" in html

    def test_modified_entry_shows_status_row(self, formatter):
        row = EntryRow(
            kind=EntryKind.BANK_ONLY, name="Modified bank",
            bank_index=0, is_modified=True,
        )

        html = formatter.format_entry(row, None)

        assert "Status" in html
        assert "Modified" in html

    def test_leaf_breakdown_in_sidebar(self, formatter):
        """The total leaf count (e.g. '61 items') used to live in the entry
        header as an inline chip — it now lives in the sidebar info panel,
        broken down by kind."""
        row = EntryRow(kind=EntryKind.TRACK, name="Dingo Canyon", song_index=0)
        leaves = [
            EntryLeaf(kind=LeafKind.SEQUENCE, name="Main", icon="🎵"),
            EntryLeaf(kind=LeafKind.SEQUENCE, name="Aku", icon="🪄"),
            EntryLeaf(kind=LeafKind.SAMPLE, name="Sample 0", icon="🔊"),
            EntryLeaf(kind=LeafKind.SAMPLE, name="Sample 1", icon="🔊"),
            EntryLeaf(kind=LeafKind.SAMPLE, name="Sample 2", icon="🔊"),
        ]

        html = formatter.format_entry(row, None, leaves)

        assert "Items" in html and ">5<" in html
        assert "Sequences" in html and ">2<" in html
        assert "Samples" in html and ">3<" in html

    def test_no_leaf_breakdown_when_leaves_empty(self, formatter):
        row = EntryRow(kind=EntryKind.OTHER_FX, name="FX 0", fx_index=0)

        html = formatter.format_entry(row, None, [])

        # Items / Samples / Sequences rows shouldn't appear at all when
        # there's nothing to break down.
        assert "Items" not in html
        assert ">Samples<" not in html
        assert ">Sequences<" not in html


class TestDocumentWrapping:

    def test_uses_document_template_with_stylesheet(self, formatter):
        """The HTML must be wrapped in `document.html` so the side panel
        picks up the same shared `style.css` the File Content details use."""
        leaf = EntryLeaf(kind=LeafKind.SAMPLE, name="X", icon="🔊", bank_index=0)

        html = formatter.format(leaf)

        assert "<html>" in html
        assert "<style>" in html
        assert ".kv" in html  # one of the shared CSS class selectors
