# coding: utf-8

import pytest

from howl_editor.gui.entry_drop_router import DropAction, EntryDropRouter
from howl_editor.gui.entries.semantic_entry import EntryRow
from howl_editor.gui.entries.semantic_entry import EntryKind


@pytest.fixture
def router():
    return EntryDropRouter()


def _row(kind: EntryKind, accepts: tuple[str, ...]) -> EntryRow:
    return EntryRow(kind=kind, name="test", accepts=accepts)


class TestTrackRouting:

    def test_cseq_routes_to_replace_song(self, router):
        row = _row(EntryKind.TRACK, (".mid", ".cseq", ".sca"))

        route = router.resolve(row, "C:\\new.cseq")

        assert route is not None
        assert route.action == DropAction.REPLACE_SONG

    def test_mid_routes_to_convert_midi(self, router):
        row = _row(EntryKind.TRACK, (".mid", ".cseq", ".sca"))

        route = router.resolve(row, "C:\\new.mid")

        assert route.action == DropAction.CONVERT_MIDI_TO_SONG

    def test_sca_routes_to_import_sca(self, router):
        row = _row(EntryKind.TRACK, (".mid", ".cseq", ".sca"))

        route = router.resolve(row, "C:\\new.sca")

        assert route.action == DropAction.IMPORT_SCA_INTO_TRACK


class TestAdventureHubRouting:

    def test_accepts_cseq_and_mid(self, router):
        row = _row(EntryKind.ADVENTURE_HUB, (".mid", ".cseq"))

        assert router.resolve(row, "x.cseq").action == DropAction.REPLACE_SONG
        assert router.resolve(row, "x.mid").action == DropAction.CONVERT_MIDI_TO_SONG

    def test_rejects_sca(self, router):
        # SCA would replace bank too, breaking the per-hub mask layering.
        row = _row(EntryKind.ADVENTURE_HUB, (".mid", ".cseq"))

        assert router.resolve(row, "x.sca") is None


class TestBankRouting:

    def test_bnk_routes_to_replace_bank(self, router):
        row = _row(EntryKind.BANK_ONLY, (".bnk",))

        assert router.resolve(row, "x.bnk").action == DropAction.REPLACE_BANK

    def test_custom_bank_same_as_bank_only(self, router):
        row = _row(EntryKind.CUSTOM_BANK, (".bnk",))

        assert router.resolve(row, "x.bnk").action == DropAction.REPLACE_BANK


class TestFxRouting:

    def test_other_fx_accepts_vag(self, router):
        row = _row(EntryKind.OTHER_FX, (".vag", ".wav"))

        assert router.resolve(row, "x.vag").action == DropAction.REPLACE_FX_SAMPLE

    def test_engine_fx_accepts_wav(self, router):
        row = _row(EntryKind.ENGINE_FX, (".vag", ".wav"))

        assert router.resolve(row, "x.wav").action == DropAction.REPLACE_FX_SAMPLE


class TestRejection:

    def test_unaccepted_extension_returns_none(self, router):
        row = _row(EntryKind.TRACK, (".mid", ".cseq"))

        assert router.resolve(row, "x.bnk") is None

    def test_empty_extension_returns_none(self, router):
        row = _row(EntryKind.TRACK, (".mid",))

        assert router.resolve(row, "noextension") is None

    def test_case_insensitive_extension(self, router):
        row = _row(EntryKind.TRACK, (".mid", ".cseq"))

        # Uppercase extension should still match.
        assert router.resolve(row, "X.CSEQ").action == DropAction.REPLACE_SONG


class TestRouteCarriesData:

    def test_route_has_path_and_row(self, router):
        row = _row(EntryKind.TRACK, (".cseq",))

        route = router.resolve(row, "path.cseq")

        assert route.file_path == "path.cseq"
        assert route.row is row
