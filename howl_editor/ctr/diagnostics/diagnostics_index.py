# coding: utf-8

from howl_editor.ctr.diagnostics.howl_diagnostics import (
    DiagnosisReport, Finding, Severity, Target, TargetKind,
)


class DiagnosticsIndex:
    """A lookup view over a `DiagnosisReport` for the GUI: what is the worst
    severity affecting a given item, and which findings explain it. Built once
    per file state and queried by the tree, cards, and detail panes."""

    def __init__(self, report: DiagnosisReport):
        self._worst: dict[Target, Severity] = {}
        self._findings: dict[Target, list[Finding]] = {}

        for finding in report.findings:
            target = finding.target
            self._findings.setdefault(target, []).append(finding)

            current = self._worst.get(target)
            if current is None or finding.severity.value > current.value:
                self._worst[target] = finding.severity

    def worst(self, target: Target) -> Severity | None:
        """Worst severity affecting exactly this target, or None."""
        return self._worst.get(target)

    def worst_for_kind(self, kind: TargetKind) -> Severity | None:
        """Worst severity across every target of a kind — for rollup badges on a
        parent node like the Banks or Songs group."""
        best: Severity | None = None
        for target, severity in self._worst.items():
            if target.kind is kind and (best is None or severity.value > best.value):
                best = severity

        return best

    def worst_overall(self) -> Severity | None:
        """Worst severity anywhere — for a rollup badge on the file root."""
        best: Severity | None = None
        for severity in self._worst.values():
            if best is None or severity.value > best.value:
                best = severity

        return best

    def findings_for(self, target: Target) -> list[Finding]:
        return self._findings.get(target, [])
