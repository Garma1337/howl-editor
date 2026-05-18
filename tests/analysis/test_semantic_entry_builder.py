# coding: utf-8

from howl_editor.models import HowlFile, EntryKind


class TestEmptyHowl:

    def test_no_groups_for_empty_file(self, semantic_entry_builder):
        groups = semantic_entry_builder.build(HowlFile())

        assert groups == []


class TestRaceTrackGroup:

    def test_single_race_track_creates_group(self, semantic_entry_builder):
        # One song (Dingo Canyon = 0) + its paired bank (Dingo Canyon = bank 1).
        # Bank 0 is universal SFX, so we need at least 2 banks.
        hwl = HowlFile(banks=[b"sfx", b"dingo"], songs=[b"dingo_song"])

        groups = semantic_entry_builder.build(hwl)

        names = [g.name for g in groups]
        assert "Race Tracks" in names

        race_tracks = next(g for g in groups if g.name == "Race Tracks")
        assert len(race_tracks.rows) == 1
        assert race_tracks.rows[0].name == "Dingo Canyon"
        assert race_tracks.rows[0].song_index == 0
        assert race_tracks.rows[0].bank_index == 1
        assert race_tracks.rows[0].kind == EntryKind.TRACK

    def test_paired_bank_omitted_when_bank_missing(self, semantic_entry_builder):
        # Song 0 present, no paired bank 1 (only universal SFX bank 0).
        hwl = HowlFile(banks=[b"sfx"], songs=[b"dingo_song"])

        groups = semantic_entry_builder.build(hwl)
        race_tracks = next(g for g in groups if g.name == "Race Tracks")

        assert race_tracks.rows[0].bank_index is None


class TestAdventureHubGroup:
    """The Adventure Hub is one entry (song 26 + bank 31). The 20-track hub
    mask is applied at *track* level inside sub-song 0 (Main music) at preview
    time — not at the row level — because the cseq only has three sub-songs
    (Main / Aku Aku / Uka Uka), like a race track."""

    def test_present_when_song_26_or_bank_31_exists(self, semantic_entry_builder):
        # 32 songs (indices 0-31) so song 26 exists; bank index 31 not needed.
        hwl = HowlFile(songs=[b""] * 32)

        groups = semantic_entry_builder.build(hwl)
        names = [g.name for g in groups]

        assert "Adventure Hub" in names

        hub_group = next(g for g in groups if g.name == "Adventure Hub")
        assert len(hub_group.rows) == 1
        assert hub_group.rows[0].kind == EntryKind.ADVENTURE_HUB
        assert hub_group.rows[0].song_index == 26
        assert hub_group.rows[0].name == "Adventure Hub"

    def test_includes_bank_when_present(self, semantic_entry_builder):
        hwl = HowlFile(songs=[b""] * 32, banks=[b""] * 32)

        groups = semantic_entry_builder.build(hwl)
        hub_group = next(g for g in groups if g.name == "Adventure Hub")

        assert hub_group.rows[0].bank_index == 31

    def test_absent_when_no_song_or_bank(self, semantic_entry_builder):
        hwl = HowlFile(songs=[b""] * 10)  # song 26 not present
        groups = semantic_entry_builder.build(hwl)

        assert "Adventure Hub" not in [g.name for g in groups]


class TestBossGroup:

    def test_shared_song_only(self, semantic_entry_builder):
        # 26 songs (0..25) — Boss Race (25) present; no boss banks.
        hwl = HowlFile(songs=[b""] * 26)

        groups = semantic_entry_builder.build(hwl)
        boss = next(g for g in groups if g.name == "Boss Themes")

        assert len(boss.rows) == 1
        assert boss.rows[0].kind == EntryKind.SHARED_SONG
        assert boss.rows[0].name == "Boss Race"


class TestCharacterGroup:

    def test_collapsed_by_default(self, semantic_entry_builder):
        # Need 55 banks to reach character bank index 54.
        hwl = HowlFile(banks=[b""] * 55)

        groups = semantic_entry_builder.build(hwl)
        characters = next(g for g in groups if g.name == "Characters")

        assert characters.collapsed_by_default is True

    def test_podium_banks_paired_with_characters(self, semantic_entry_builder):
        """Each character's main bank is immediately followed by its podium
        bank (offset -17). A full stock HOWL has 71 banks (0-70)."""
        hwl = HowlFile(banks=[b""] * 71)

        groups = semantic_entry_builder.build(hwl)
        characters = next(g for g in groups if g.name == "Characters")
        bank_order = [row.bank_index for row in characters.rows]

        # Bank 54 = "8-Driver Shared", no podium.
        # Bank 55 = Crash, paired with podium 38.
        # Bank 70 = Oxide, paired with podium 53.
        assert bank_order[:5] == [54, 55, 38, 56, 39]
        assert bank_order[-2:] == [70, 53]

    def test_shared_driver_bank_54_has_no_podium_row(self, semantic_entry_builder):
        """Bank 54 is the 8-Driver Shared bank, not a character — it must not
        emit a podium row (54 - 17 = 37, which is the Credits bank)."""
        hwl = HowlFile(banks=[b""] * 55)

        groups = semantic_entry_builder.build(hwl)
        characters = next(g for g in groups if g.name == "Characters")

        assert [row.bank_index for row in characters.rows] == [54]


class TestModifiedDetection:

    def test_modified_song_marks_row(self, semantic_entry_builder):
        hwl = HowlFile(banks=[b"sfx", b"dingo"], songs=[b"NEW_song"])
        original_songs = [b"ORIGINAL_song"]
        original_banks = [b"sfx", b"dingo"]

        groups = semantic_entry_builder.build(hwl, original_banks, original_songs)
        track = next(g for g in groups if g.name == "Race Tracks").rows[0]

        assert track.is_modified is True

    def test_unchanged_song_not_modified(self, semantic_entry_builder):
        hwl = HowlFile(banks=[b"sfx", b"dingo"], songs=[b"song"])

        groups = semantic_entry_builder.build(hwl, [b"sfx", b"dingo"], [b"song"])
        track = next(g for g in groups if g.name == "Race Tracks").rows[0]

        assert track.is_modified is False

    def test_modified_paired_bank_marks_row(self, semantic_entry_builder):
        hwl = HowlFile(banks=[b"sfx", b"NEW_dingo"], songs=[b"song"])

        groups = semantic_entry_builder.build(hwl, [b"sfx", b"old"], [b"song"])
        track = next(g for g in groups if g.name == "Race Tracks").rows[0]

        assert track.is_modified is True


class TestCustomGroup:

    def test_custom_song_appears_in_custom_group(self, semantic_entry_builder):
        # 34 songs: index 33 is the first custom slot.
        hwl = HowlFile(songs=[b""] * 34)

        groups = semantic_entry_builder.build(hwl)
        custom = next(g for g in groups if g.name == "Custom")

        assert any(r.kind == EntryKind.CUSTOM_SONG and r.song_index == 33 for r in custom.rows)


class TestFxGroups:

    def test_other_fx_entry_per_row(self, semantic_entry_builder, sample_howl):
        groups = semantic_entry_builder.build(sample_howl)
        other_fx = next(g for g in groups if g.name == "Sound Effects (OtherFX)")

        assert len(other_fx.rows) == len(sample_howl.other_fx)
        assert other_fx.rows[0].kind == EntryKind.OTHER_FX

    def test_engine_fx_entry_per_row(self, semantic_entry_builder, sample_howl):
        groups = semantic_entry_builder.build(sample_howl)
        engine_fx = next(g for g in groups if g.name == "Engine Sounds (EngineFX)")

        assert len(engine_fx.rows) == len(sample_howl.engine_fx)
        assert engine_fx.rows[0].kind == EntryKind.ENGINE_FX


class TestAcceptedDropExtensions:

    def test_track_accepts_music_and_sca(self, semantic_entry_builder):
        hwl = HowlFile(banks=[b"sfx", b"dingo"], songs=[b"song"])

        groups = semantic_entry_builder.build(hwl)
        track = next(g for g in groups if g.name == "Race Tracks").rows[0]

        assert ".mid" in track.accepts
        assert ".cseq" in track.accepts
        assert ".sca" in track.accepts

    def test_character_bank_accepts_bnk(self, semantic_entry_builder):
        hwl = HowlFile(banks=[b""] * 55)

        groups = semantic_entry_builder.build(hwl)
        char_row = next(g for g in groups if g.name == "Characters").rows[0]

        assert char_row.accepts == (".bnk",)
