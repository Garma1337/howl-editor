# coding: utf-8

import pytest

from howl_editor.gui.category_icon_resolver import CategoryIconResolver


@pytest.fixture
def resolver(tmp_path):
    return CategoryIconResolver(tmp_path)


class TestSlugify:

    def test_simple_lowercase(self):
        assert CategoryIconResolver.slugify("Race Tracks") == "race_tracks"

    def test_ampersand_becomes_and(self):
        assert CategoryIconResolver.slugify("Menus & Cinematics") == "menus_and_cinematics"

    def test_parens_collapse_to_underscore(self):
        assert CategoryIconResolver.slugify("SFX (universal)") == "sfx_universal"

    def test_strips_trailing_underscores(self):
        # Wrapping punctuation should not leave dangling underscores.
        assert CategoryIconResolver.slugify("(Custom)") == "custom"

    def test_collapses_repeated_separators(self):
        assert CategoryIconResolver.slugify("Foo   ---  Bar") == "foo_bar"

    def test_empty_input(self):
        assert CategoryIconResolver.slugify("") == ""

    def test_ampersand_expansion_is_literal(self):
        # Each `&` is replaced with `and` BEFORE the underscore collapse, so
        # consecutive ampersands stack rather than collapsing to one word.
        assert CategoryIconResolver.slugify("   &&&   ") == "andandand"


class TestResolve:

    def test_returns_none_when_missing(self, resolver):
        assert resolver.resolve("Race Tracks") is None

    def test_finds_png(self, resolver, tmp_path):
        target = tmp_path / "race_tracks.png"
        target.write_bytes(b"")

        result = resolver.resolve("Race Tracks")
        assert result == target

    def test_finds_jpg(self, resolver, tmp_path):
        target = tmp_path / "characters.jpg"
        target.write_bytes(b"")

        assert resolver.resolve("Characters") == target

    def test_png_wins_over_jpg(self, resolver, tmp_path):
        # Both formats exist; the resolver should prefer PNG (listed first).
        png = tmp_path / "characters.png"
        jpg = tmp_path / "characters.jpg"
        png.write_bytes(b"")
        jpg.write_bytes(b"")

        assert resolver.resolve("Characters") == png

    def test_handles_special_chars_in_name(self, resolver, tmp_path):
        target = tmp_path / "menus_and_cinematics.svg"
        target.write_bytes(b"")

        assert resolver.resolve("Menus & Cinematics") == target

    def test_returns_none_for_empty_name(self, resolver):
        assert resolver.resolve("") is None

    def test_sub_dir_lookup(self, resolver, tmp_path):
        # Per-entry icon: images/characters/crash_bandicoot.png
        char_dir = tmp_path / "characters"
        char_dir.mkdir()
        target = char_dir / "crash_bandicoot.png"
        target.write_bytes(b"")

        # Direct resolve with sub_dir should find it.
        assert resolver.resolve("Crash Bandicoot", sub_dir="Characters") == target

    def test_sub_dir_missing_returns_none(self, resolver):
        assert resolver.resolve("Crash Bandicoot", sub_dir="Characters") is None

    def test_root_lookup_ignores_sub_dir_files(self, resolver, tmp_path):
        # A subdir file should NOT match when resolve() is called without sub_dir.
        (tmp_path / "characters").mkdir()
        (tmp_path / "characters" / "crash.png").write_bytes(b"")

        assert resolver.resolve("Crash") is None


class TestResolveEntry:

    def test_finds_per_entry_icon(self, resolver, tmp_path):
        (tmp_path / "boss_themes").mkdir()
        target = tmp_path / "boss_themes" / "boss_papu_papu.png"
        target.write_bytes(b"")

        result = resolver.resolve_entry("Boss: Papu Papu", "Boss Themes")
        assert result == target

    def test_returns_none_when_no_match(self, resolver):
        assert resolver.resolve_entry("Sewer Speedway", "Race Tracks") is None

    def test_podium_entries_use_shared_icon(self, resolver, tmp_path):
        """All "<character> (Podium)" entries resolve to a single shared
        `characters/podium.<ext>` instead of needing a per-character file."""
        (tmp_path / "characters").mkdir()
        shared = tmp_path / "characters" / "podium.png"
        shared.write_bytes(b"")

        assert resolver.resolve_entry("Crash Bandicoot (Podium)", "Characters") == shared
        assert resolver.resolve_entry("Oxide (Podium)", "Characters") == shared
        assert resolver.resolve_entry("Penta Penguin (Podium)", "Characters") == shared

    def test_podium_does_not_affect_main_character_lookup(self, resolver, tmp_path):
        """The main character row still resolves to its own per-character icon
        — only the podium suffix re-routes to the shared file."""
        (tmp_path / "characters").mkdir()
        crash = tmp_path / "characters" / "crash_bandicoot.png"
        crash.write_bytes(b"")

        assert resolver.resolve_entry("Crash Bandicoot", "Characters") == crash


class TestResolveLeaf:

    def test_finds_aku_aku_mask(self, resolver, tmp_path):
        (tmp_path / "leaves").mkdir()
        target = tmp_path / "leaves" / "aku_aku_mask.png"
        target.write_bytes(b"")

        assert resolver.resolve_leaf("Aku Aku mask") == target

    def test_finds_uka_uka_mask(self, resolver, tmp_path):
        (tmp_path / "leaves").mkdir()
        target = tmp_path / "leaves" / "uka_uka_mask.svg"
        target.write_bytes(b"")

        assert resolver.resolve_leaf("Uka Uka mask") == target

    def test_returns_none_when_no_match(self, resolver):
        assert resolver.resolve_leaf("Main music") is None
