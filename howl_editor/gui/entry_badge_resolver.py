# coding: utf-8

from howl_editor.ctr.diagnostics.howl_diagnostics import Severity, Target, TargetKind
from howl_editor.gui.severity_presenter import SeverityPresenter

# Only these severities warrant a badge on a bank/song row or card.
_BADGED = (Severity.ERROR, Severity.WARNING)


class EntryBadgeResolver:
    """Turns a `DiagnosticsIndex` plus a category row/group into the status
    emoji the card and detail views show. Keeps the widgets free of the
    diagnostics types — they just display the string this returns."""

    def __init__(self, severity_presenter: SeverityPresenter):
        self._presenter = severity_presenter

    def row_badge(self, index, row) -> str:
        """Worst-severity emoji for one entry row (a track carries both a song
        and a bank target), or '' when the row is clean / there is no index."""
        return self._emoji(self._row_severity(index, row))

    def group_badge(self, index, group) -> str:
        """Worst-severity emoji across every row in a category card's group."""
        if index is None:
            return ""

        worst = None
        for row in group.rows:
            severity = self._row_severity(index, row)
            if severity is not None and (worst is None or severity.value > worst.value):
                worst = severity

        return self._emoji(worst)

    def row_label(self, index, row) -> str:
        """The short severity label shown on an entry's pill (e.g. 'Error
        detected'), sourced from the presenter so it matches the sidebar
        banner heading. '' when the row is clean."""
        severity = self._row_severity(index, row)
        if severity not in _BADGED:
            return ""

        return self._presenter.heading(severity)

    def row_findings(self, index, row) -> list:
        """Every diagnosis finding affecting an entry row — used to show the
        explanatory banner / tooltip, not just the icon."""
        if index is None:
            return []

        out = []
        for target in self._targets(row):
            out.extend(index.findings_for(target))
        return out

    def leaf_findings(self, index, leaf) -> list:
        """Findings affecting a leaf's parent bank (a sample) or song (a
        sequence) — a leaf inherits its container's engine-limit problems."""
        if index is None:
            return []

        out = []
        for target in self._leaf_targets(leaf):
            out.extend(index.findings_for(target))
        
        return out

    def _emoji(self, severity) -> str:
        if severity not in _BADGED:
            return ""

        return self._presenter.emoji(severity)

    def _row_severity(self, index, row):
        if index is None:
            return None

        worst = None
        for target in self._targets(row):
            severity = index.worst(target)
            if severity is not None and (worst is None or severity.value > worst.value):
                worst = severity

        return worst

    def _targets(self, row) -> list[Target]:
        targets: list[Target] = []
        if getattr(row, "song_index", None) is not None:
            targets.append(Target(TargetKind.SONG, row.song_index))

        if getattr(row, "bank_index", None) is not None:
            targets.append(Target(TargetKind.BANK, row.bank_index))

        return targets

    def _leaf_targets(self, leaf) -> list[Target]:
        # A sample leaf carries a bank_index; a sequence leaf a song_index.
        targets: list[Target] = []
        if getattr(leaf, "bank_index", None) is not None:
            targets.append(Target(TargetKind.BANK, leaf.bank_index))

        if getattr(leaf, "song_index", None) is not None:
            targets.append(Target(TargetKind.SONG, leaf.song_index))

        return targets
