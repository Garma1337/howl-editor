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


class TestCustomBoundaries:

    def test_custom_song(self, stock_layout):
        assert stock_layout.is_custom_song(32) is False
        assert stock_layout.is_custom_song(33) is True
        assert stock_layout.is_custom_song(99) is True

    def test_custom_bank(self, stock_layout):
        assert stock_layout.is_custom_bank(70) is False
        assert stock_layout.is_custom_bank(71) is True
        assert stock_layout.is_custom_bank(99) is True
