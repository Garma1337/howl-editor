# coding: utf-8

from howl_editor.cseq.adventure_hub import AdventureHubMaskTable


class TestSequencesForHub:

    def test_gem_stone_valley_includes_always_on_and_hub0_only(self, adventure_hub_mask_table):
        # Hub 0 (GSV) hears bit-0 sequences: 0x1F includes it, 0x01 is GSV-only.
        sequences = adventure_hub_mask_table.sequences_for_hub(0)

        assert 0 in sequences   # 0x1F — always on
        assert 1 in sequences   # 0x17 — GSV included
        assert 6 in sequences   # 0x01 — GSV only
        assert 2 not in sequences  # 0x08 — Glacier only

    def test_glacier_park_excludes_gsv_only_sequences(self, adventure_hub_mask_table):
        sequences = adventure_hub_mask_table.sequences_for_hub(3)

        assert 2 in sequences   # 0x08 — Glacier only
        assert 0 in sequences   # 0x1F — always on
        assert 6 not in sequences  # 0x01 — GSV only
        assert 14 not in sequences  # 0x02 — NSB only


class TestHubsForSequence:

    def test_always_on_sequence_lists_all_hubs(self, adventure_hub_mask_table):
        # Sequence 0 has mask 0x1F (all 5 hubs).
        hubs = adventure_hub_mask_table.hubs_for_sequence(0)

        assert hubs == [0, 1, 2, 3, 4]

    def test_single_hub_sequence(self, adventure_hub_mask_table):
        # Sequence 2 has mask 0x08 (Glacier Park only).
        assert adventure_hub_mask_table.hubs_for_sequence(2) == [3]

    def test_out_of_range_returns_empty(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.hubs_for_sequence(999) == []


class TestSequenceHubMatrix:

    def test_dimensions(self, adventure_hub_mask_table):
        matrix = adventure_hub_mask_table.sequence_hub_matrix()

        assert len(matrix) == 20  # 20 sequences
        for row in matrix:
            assert len(row) == 5  # 5 hubs

    def test_first_row_all_true(self, adventure_hub_mask_table):
        matrix = adventure_hub_mask_table.sequence_hub_matrix()

        assert matrix[0] == [True, True, True, True, True]

    def test_glacier_only_row(self, adventure_hub_mask_table):
        matrix = adventure_hub_mask_table.sequence_hub_matrix()

        assert matrix[2] == [False, False, False, True, False]


class TestProperties:

    def test_num_sequences(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.num_sequences == 20

    def test_num_hubs(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.num_hubs == 5

    def test_hub_names_in_order(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.hub_name(0) == "Gem Stone Valley"
        assert adventure_hub_mask_table.hub_name(4) == "Citadel City"


class TestInjectability:

    def test_accepts_custom_mask_and_names(self):
        custom_mask = (0x03, 0x01)
        custom_names = ("Hub A", "Hub B")
        table = AdventureHubMaskTable(custom_mask, custom_names)

        assert table.num_sequences == 2
        assert table.num_hubs == 2
        assert table.hubs_for_sequence(0) == [0, 1]
        assert table.hubs_for_sequence(1) == [0]
