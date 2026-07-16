# coding: utf-8

from howl_editor.ctr.diagnostics.diagnostics_index import DiagnosticsIndex
from howl_editor.ctr.diagnostics.howl_diagnostics import (
    Category, DiagnosisReport, Finding, Severity, Target, TargetKind,
)


def _report(*findings) -> DiagnosisReport:
    return DiagnosisReport(findings=list(findings))


def _finding(severity, target, category=Category.CSEQ_SIZE):
    return Finding(severity, category, target, "msg")


class TestDiagnosticsIndex:

    def test_worst_takes_the_highest_severity_on_a_target(self):
        song0 = Target(TargetKind.SONG, 0)
        index = DiagnosticsIndex(_report(
            _finding(Severity.WARNING, song0),
            _finding(Severity.ERROR, song0),
        ))

        assert index.worst(song0) is Severity.ERROR

    def test_worst_is_none_for_untouched_target(self):
        index = DiagnosticsIndex(_report(
            _finding(Severity.ERROR, Target(TargetKind.SONG, 0)),
        ))

        assert index.worst(Target(TargetKind.BANK, 5)) is None

    def test_worst_for_kind_rolls_up_over_all_indices(self):
        index = DiagnosticsIndex(_report(
            _finding(Severity.WARNING, Target(TargetKind.BANK, 1)),
            _finding(Severity.ERROR, Target(TargetKind.BANK, 9)),
            _finding(Severity.INFO, Target(TargetKind.SONG, 0)),
        ))

        assert index.worst_for_kind(TargetKind.BANK) is Severity.ERROR
        assert index.worst_for_kind(TargetKind.SONG) is Severity.INFO
        assert index.worst_for_kind(TargetKind.FILE) is None

    def test_worst_overall(self):
        index = DiagnosticsIndex(_report(
            _finding(Severity.INFO, Target(TargetKind.FILE)),
            _finding(Severity.WARNING, Target(TargetKind.SONG, 2)),
        ))

        assert index.worst_overall() is Severity.WARNING

    def test_findings_for_returns_the_targets_findings(self):
        song0 = Target(TargetKind.SONG, 0)
        a = _finding(Severity.ERROR, song0, Category.CSEQ_SIZE)
        b = _finding(Severity.WARNING, song0, Category.SAMPLE_REFERENCE)
        index = DiagnosticsIndex(_report(a, b, _finding(Severity.INFO, Target(TargetKind.FILE))))

        assert index.findings_for(song0) == [a, b]
