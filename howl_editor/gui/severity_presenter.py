# coding: utf-8

from howl_editor.ctr.diagnostics.howl_diagnostics import Severity


class SeverityPresenter:
    """Single source of truth for how a diagnosis `Severity` is shown: the
    status emoji (tree rows, cards, the report list), the CSS class used by the
    detail-pane banner, and the banner heading. Consolidates mappings that were
    otherwise repeated across the tree, the badge resolver, and the dialog."""

    _EMOJI = {
        Severity.ERROR: "❌",
        Severity.WARNING: "⚠️",
        Severity.INFO: "ℹ️",
    }

    _CSS_CLASS = {
        Severity.ERROR: "error",
        Severity.WARNING: "warning",
        Severity.INFO: "info",
    }

    _HEADING = {
        Severity.ERROR: "Error detected",
        Severity.WARNING: "Issue detected",
        Severity.INFO: "Information",
    }

    def emoji(self, severity: Severity | None) -> str:
        return self._EMOJI.get(severity, "")

    def css_class(self, severity: Severity | None) -> str:
        return self._CSS_CLASS.get(severity, "")

    def heading(self, severity: Severity | None) -> str:
        return self._HEADING.get(severity, "")
