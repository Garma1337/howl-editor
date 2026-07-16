# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.diagnostics.howl_diagnostics import (
    Category, DiagnosisReport, Finding, Severity, Target, TargetKind,
)
from howl_editor.gui.dialog.diagnosis_report_dialog import DiagnosisReportDialog


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _report(*findings) -> DiagnosisReport:
    return DiagnosisReport(findings=list(findings))


class TestDiagnosisReportDialog:

    def test_renders_all_findings(self, qt_app):
        report = _report(
            Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, 3), "too big"),
            Finding(Severity.WARNING, Category.SAMPLE_REFERENCE, Target(TargetKind.SONG, 5), "foreign"),
            Finding(Severity.INFO, Category.SUMMARY, Target(TargetKind.FILE), "ok"),
        )

        dlg = DiagnosisReportDialog(None, report)

        assert dlg._list.count() == 3

    def test_empty_report_does_not_crash(self, qt_app):
        dlg = DiagnosisReportDialog(None, _report())

        assert dlg._list.count() == 0

    def test_copy_produces_a_line_per_finding_plus_header(self, qt_app):
        report = _report(
            Finding(Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, 3), "m"),
            Finding(Severity.WARNING, Category.SPU_RESIDENCY, Target(TargetKind.BANK, 4), "m"),
        )

        dlg = DiagnosisReportDialog(None, report)
        lines = [ln for ln in dlg._plain_text().splitlines() if ln.strip()]

        # A header line plus one line per finding — structure, not wording.
        assert len(lines) == 1 + len(report.findings)
