# coding: utf-8

from howl_editor.analysis.stock_names import StockNames


class TestBankNames:

    def test_sfx_universal(self, stock_names):
        assert stock_names.bank_name(0) == "SFX (universal)"

    def test_race_track_bank(self, stock_names):
        assert stock_names.bank_name(9) == "Sewer Speedway"

    def test_battle_arena_bank(self, stock_names):
        assert stock_names.bank_name(19) == "Nitro Court"

    def test_adventure_hub_bank(self, stock_names):
        assert stock_names.bank_name(31) == "Adventure Hub"

    def test_main_menu_bank(self, stock_names):
        assert stock_names.bank_name(32) == "Main Menu"

    def test_character_bank(self, stock_names):
        assert stock_names.bank_name(55) == "Crash Bandicoot"

    def test_custom_bank_label(self, stock_names):
        assert stock_names.bank_name(71) == "Custom"
        assert stock_names.bank_name(999) == "Custom"

    def test_unknown_in_range_returns_empty(self, stock_names):
        # 38-53 are not assigned a name in the stock table.
        assert stock_names.bank_name(38) == ""


class TestSongNames:

    def test_race_track_song(self, stock_names):
        assert stock_names.song_name(8) == "Sewer Speedway"

    def test_battle_arena_song(self, stock_names):
        assert stock_names.song_name(18) == "Nitro Court"

    def test_boss_race_song_is_shared(self, stock_names):
        assert stock_names.song_name(25) == "Boss Race"

    def test_adventure_hub_song(self, stock_names):
        assert stock_names.song_name(26) == "Adventure Hub"

    def test_song_27_is_main_menu_not_character_select(self, stock_names):
        # Regression guard for the original mismatch — bank 32 and song 27
        # point to the SAME in-game asset and must share a name.
        assert stock_names.song_name(27) == "Main Menu"
        assert stock_names.song_name(27) == stock_names.bank_name(32)

    def test_credits_song(self, stock_names):
        assert stock_names.song_name(32) == "Credits"

    def test_custom_song_label(self, stock_names):
        assert stock_names.song_name(33) == "Custom"


class TestPairedNamesAgree:

    def test_race_tracks_share_names(self, stock_names):
        # Each race-track song N (0-17) should match bank N+1.
        for song_idx in range(18):
            assert stock_names.song_name(song_idx) == stock_names.bank_name(song_idx + 1), \
                f"Mismatch for song {song_idx}"

    def test_battle_arenas_share_names(self, stock_names):
        # Battle-arena song N (18-24) should match bank N+1.
        for song_idx in range(18, 25):
            assert stock_names.song_name(song_idx) == stock_names.bank_name(song_idx + 1)

    def test_menu_songs_share_bank_names(self, stock_names):
        # Menu / cinematic songs 27-32 should match banks 32-37.
        for song_idx in range(27, 33):
            assert stock_names.song_name(song_idx) == stock_names.bank_name(song_idx + 5)
