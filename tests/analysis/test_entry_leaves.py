# coding: utf-8

from howl_editor.analysis.entry_leaves import EntryLeavesBuilder
from howl_editor.models import EntryRow, HowlFile, LeafKind, SpuAddrEntry
from howl_editor.models.semantic_entry import EntryKind
from tests.conftest import build_bank_blob, build_cseq_bytes


def _builder(bank_reader, cseq_reader, track_mask_layout):
    return EntryLeavesBuilder(bank_reader, cseq_reader, track_mask_layout)


class TestSongLeaves:

    def test_named_mask_slots_for_song_in_range(self, bank_reader, cseq_reader, track_mask_layout):
        from howl_editor.models import CseqSong, CseqTrack, CseqEvent, CseqEventType

        # Build a song with 3 sequences — for song_index 8 (Sewer Speedway).
        track = CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        cseq_bytes = build_cseq_bytes(songs=[
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
        ])

        hwl = HowlFile(songs=[b""] * 8 + [cseq_bytes])
        row = EntryRow(kind=EntryKind.TRACK, name="Sewer Speedway", song_index=8)

        leaves = _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row)

        assert len(leaves) == 3
        assert leaves[0].name == "Main music"
        assert leaves[1].name == "Aku Aku mask"
        assert leaves[2].name == "Uka Uka mask"
        assert leaves[0].kind == LeafKind.SEQUENCE
        assert leaves[0].song_index == 8
        assert leaves[0].seq_index == 0

    def test_generic_names_for_song_outside_mask_range(self, bank_reader, cseq_reader, track_mask_layout):
        from howl_editor.models import CseqSong, CseqTrack, CseqEvent, CseqEventType

        track = CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        cseq_bytes = build_cseq_bytes(songs=[
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
            CseqSong(bpm=120, tpqn=480, tracks=[track]),
        ])

        # Song index 40 — beyond the mask range.
        hwl = HowlFile(songs=[b""] * 40 + [cseq_bytes])
        row = EntryRow(kind=EntryKind.CUSTOM_SONG, name="Custom", song_index=40)

        leaves = _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row)

        assert [leaf.name for leaf in leaves] == ["Sequence 0", "Sequence 1"]


class TestBankLeaves:

    def test_one_leaf_per_sample(self, bank_reader, cseq_reader, track_mask_layout):
        spu = [SpuAddrEntry(0, 2)] * 5
        bank_blob = build_bank_blob([1, 3], [b"\x00" * 16, b"\x00" * 16])
        hwl = HowlFile(spu_addrs=spu, banks=[bank_blob])

        row = EntryRow(kind=EntryKind.BANK_ONLY, name="Test", bank_index=0)
        leaves = _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row)

        assert len(leaves) == 2
        assert leaves[0].kind == LeafKind.SAMPLE
        assert leaves[0].bank_index == 0
        assert leaves[0].sample_index == 0
        assert leaves[0].spu_index == 1
        assert leaves[1].spu_index == 3


class TestFxEntries:

    def test_other_fx_has_no_sub_leaves(self, bank_reader, cseq_reader, track_mask_layout):
        # FX entries are themselves single playable units; no nested leaves.
        hwl = HowlFile()
        row = EntryRow(kind=EntryKind.OTHER_FX, name="FX 0", fx_index=0)

        assert _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row) == []

    def test_engine_fx_has_no_sub_leaves(self, bank_reader, cseq_reader, track_mask_layout):
        hwl = HowlFile()
        row = EntryRow(kind=EntryKind.ENGINE_FX, name="Engine 0", fx_index=0)

        assert _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row) == []


class TestCombinedEntry:

    def test_track_with_paired_bank_lists_both_sets(self, bank_reader, cseq_reader, track_mask_layout):
        from howl_editor.models import CseqSong, CseqTrack, CseqEvent, CseqEventType

        track = CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        cseq_bytes = build_cseq_bytes(songs=[CseqSong(bpm=120, tpqn=480, tracks=[track])])

        spu = [SpuAddrEntry(0, 2)] * 5
        bank_blob = build_bank_blob([1], [b"\x00" * 16])
        hwl = HowlFile(spu_addrs=spu, banks=[b"sfx", bank_blob], songs=[cseq_bytes])

        # Race track entry references song 0 + bank 1.
        row = EntryRow(kind=EntryKind.TRACK, name="Dingo Canyon", song_index=0, bank_index=1)

        leaves = _builder(bank_reader, cseq_reader, track_mask_layout).build(hwl, row)

        # 1 song sequence + 1 bank sample = 2 leaves total.
        kinds = [leaf.kind for leaf in leaves]
        assert LeafKind.SEQUENCE in kinds
        assert LeafKind.SAMPLE in kinds
