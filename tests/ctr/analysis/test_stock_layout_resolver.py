# coding: utf-8


class TestPairedBank:

    def test_race_track_songs_pair_with_bank_plus_one(self, stock_layout):
        # Song 0 (Dingo Canyon) → bank 1, song 17 → bank 18
        assert stock_layout.paired_bank(0) == 1
        assert stock_layout.paired_bank(8) == 9     # Sewer Speedway
        assert stock_layout.paired_bank(17) == 18

    def test_battle_arena_songs_pair_with_bank_plus_one(self, stock_layout):
        # Song 18 (Nitro Court) → bank 19, song 24 → bank 25
        assert stock_layout.paired_bank(18) == 19
        assert stock_layout.paired_bank(24) == 25

    def test_menu_songs_pair_with_bank_plus_five(self, stock_layout):
        # Song 27 (Character Select) → bank 32
        assert stock_layout.paired_bank(27) == 32
        assert stock_layout.paired_bank(32) == 37

    def test_boss_song_has_no_paired_bank(self, stock_layout):
        # Boss Race (song 25) is shared across boss banks 26-30; no 1:1 pair.
        assert stock_layout.paired_bank(25) is None

    def test_custom_song_has_no_paired_bank(self, stock_layout):
        assert stock_layout.paired_bank(100) is None


class TestCategoryQueries:

    def test_race_track_song_boundaries(self, stock_layout):
        assert stock_layout.is_race_track_song(0) is True
        assert stock_layout.is_race_track_song(17) is True
        assert stock_layout.is_race_track_song(18) is False

    def test_battle_arena_song_boundaries(self, stock_layout):
        assert stock_layout.is_battle_arena_song(18) is True
        assert stock_layout.is_battle_arena_song(24) is True
        assert stock_layout.is_battle_arena_song(25) is False

    def test_menu_song_boundaries(self, stock_layout):
        assert stock_layout.is_menu_song(27) is True
        assert stock_layout.is_menu_song(32) is True
        assert stock_layout.is_menu_song(26) is False
        assert stock_layout.is_menu_song(33) is False

    def test_character_bank_boundaries(self, stock_layout):
        assert stock_layout.is_character_bank(54) is True
        assert stock_layout.is_character_bank(70) is True
        assert stock_layout.is_character_bank(53) is False
        assert stock_layout.is_character_bank(71) is False

    def test_boss_bank_boundaries(self, stock_layout):
        assert stock_layout.is_boss_bank(26) is True
        assert stock_layout.is_boss_bank(30) is True
        assert stock_layout.is_boss_bank(25) is False
        assert stock_layout.is_boss_bank(31) is False


class TestPodiumBanks:
    """Banks 38-53 are character podium-animation banks. Each one pairs to
    the matching character bank exactly 17 slots higher."""

    def test_podium_bank_boundaries(self, stock_layout):
        assert stock_layout.is_podium_bank(38) is True
        assert stock_layout.is_podium_bank(53) is True
        assert stock_layout.is_podium_bank(37) is False
        assert stock_layout.is_podium_bank(54) is False

    def test_podium_bank_for_character_pairs_with_offset_17(self, stock_layout):
        # Crash Bandicoot (55) → podium 38, Oxide (70) → podium 53.
        assert stock_layout.podium_bank_for_character(55) == 38
        assert stock_layout.podium_bank_for_character(70) == 53

    def test_shared_driver_bank_54_has_no_podium(self, stock_layout):
        # 54 is the "8-Driver Shared" bank — it does not represent a character
        # and there is no podium bank at index 37 (which is the Credits bank).
        assert stock_layout.podium_bank_for_character(54) is None


class TestCustomBoundaries:

    def test_custom_song(self, stock_layout):
        assert stock_layout.is_custom_song(32) is False
        assert stock_layout.is_custom_song(33) is True
        assert stock_layout.is_custom_song(99) is True

    def test_custom_bank(self, stock_layout):
        assert stock_layout.is_custom_bank(70) is False
        assert stock_layout.is_custom_bank(71) is True
        assert stock_layout.is_custom_bank(99) is True
