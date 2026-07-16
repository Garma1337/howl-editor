# coding: utf-8

from types import SimpleNamespace

from howl_editor.ctr.diagnostics.diagnostics_index import DiagnosticsIndex
from howl_editor.ctr.diagnostics.howl_diagnostics import (
    Category, DiagnosisReport, Finding, Severity, Target, TargetKind,
)
from howl_editor.gui.entry_badge_resolver import EntryBadgeResolver
from howl_editor.gui.severity_presenter import SeverityPresenter


def _resolver() -> EntryBadgeResolver:
    return EntryBadgeResolver(SeverityPresenter())


def _index(*findings) -> DiagnosticsIndex:
    return DiagnosticsIndex(DiagnosisReport(findings=list(findings)))


def _row(song_index=None, bank_index=None):
    return SimpleNamespace(song_index=song_index, bank_index=bank_index)


def _group(*rows):
    return SimpleNamespace(rows=list(rows))


class TestEntryBadgeResolver:

    def test_no_index_gives_no_badge(self):
        assert _resolver().row_badge(None, _row(song_index=3)) == ""

    def test_song_error_badges_the_row(self):
        index = _index(Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, 3), "m"))

        assert _resolver().row_badge(index, _row(song_index=3)) == "❌"

    def test_bank_warning_badges_the_row(self):
        index = _index(Finding(Severity.WARNING, Category.SPU_RESIDENCY, Target(TargetKind.BANK, 4), "m"))

        assert _resolver().row_badge(index, _row(bank_index=4)) == "⚠️"

    def test_track_takes_worst_of_song_and_bank(self):
        index = _index(
            Finding(Severity.WARNING, Category.SPU_RESIDENCY, Target(TargetKind.SONG, 3), "m"),
            Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.BANK, 4), "m"),
        )
        row = _row(song_index=3, bank_index=4)

        assert _resolver().row_badge(index, row) == "❌"

    def test_clean_row_has_no_badge(self):
        index = _index(Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, 9), "m"))

        assert _resolver().row_badge(index, _row(song_index=3)) == ""

    def test_group_badge_is_worst_across_rows(self):
        index = _index(Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, 3), "m"))
        group = _group(_row(song_index=1), _row(song_index=3), _row(bank_index=2))

        assert _resolver().group_badge(index, group) == "❌"
