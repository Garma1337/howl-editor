# coding: utf-8

from howl_editor.cseq.adventure_hub import AdventureHubMaskTable


class TestTracksForHub:

    def test_gem_stone_valley_includes_always_on_and_hub0_only(self, adventure_hub_mask_table):
        # Hub 0 (GSV) hears bit-0 tracks: 0x1F includes it, 0x01 is GSV-only.
        tracks = adventure_hub_mask_table.tracks_for_hub(0)

        assert 0 in tracks   # 0x1F — always on
        assert 1 in tracks   # 0x17 — GSV included
        assert 6 in tracks   # 0x01 — GSV only
        assert 2 not in tracks  # 0x08 — Glacier only

    def test_glacier_park_excludes_gsv_only_tracks(self, adventure_hub_mask_table):
        tracks = adventure_hub_mask_table.tracks_for_hub(3)

        assert 2 in tracks   # 0x08 — Glacier only
        assert 0 in tracks   # 0x1F — always on
        assert 6 not in tracks  # 0x01 — GSV only
        assert 14 not in tracks  # 0x02 — NSB only

    def test_each_hub_yields_different_track_set(self, adventure_hub_mask_table):
        """Sanity check the data: every hub must have a distinct active-track
        list — that's the whole point of the per-hub mask."""
        sets = [
            tuple(adventure_hub_mask_table.tracks_for_hub(h))
            for h in range(adventure_hub_mask_table.num_hubs)
        ]

        assert len(set(sets)) == adventure_hub_mask_table.num_hubs


class TestTrackIsActiveInHub:

    def test_always_on_track(self, adventure_hub_mask_table):
        # Track 0 mask 0x1F = audible in every hub.
        for h in range(adventure_hub_mask_table.num_hubs):
            assert adventure_hub_mask_table.track_is_active_in_hub(0, h)

    def test_glacier_only_track(self, adventure_hub_mask_table):
        # Track 2 mask 0x08 = Glacier Park (hub 3) only.
        assert not adventure_hub_mask_table.track_is_active_in_hub(2, 0)
        assert adventure_hub_mask_table.track_is_active_in_hub(2, 3)
        assert not adventure_hub_mask_table.track_is_active_in_hub(2, 4)


class TestHubsForTrack:

    def test_always_on_track_lists_all_hubs(self, adventure_hub_mask_table):
        # Track 0 has mask 0x1F (all 5 hubs).
        hubs = adventure_hub_mask_table.hubs_for_track(0)

        assert hubs == [0, 1, 2, 3, 4]

    def test_single_hub_track(self, adventure_hub_mask_table):
        # Track 2 has mask 0x08 (Glacier Park only).
        assert adventure_hub_mask_table.hubs_for_track(2) == [3]

    def test_out_of_range_returns_empty(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.hubs_for_track(999) == []


class TestProperties:

    def test_num_tracks(self, adventure_hub_mask_table):
        assert adventure_hub_mask_table.num_tracks == 20

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

        assert table.num_tracks == 2
        assert table.num_hubs == 2
        assert table.hubs_for_track(0) == [0, 1]
        assert table.hubs_for_track(1) == [0]
