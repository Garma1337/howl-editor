# coding: utf-8

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.ctr.diagnostics.howl_diagnostics import Finding, Severity
from howl_editor.gui.severity_presenter import SeverityPresenter


class DiagnosisBannerFormatter:
    """Renders the coloured warning banner shown at the top of a flagged
    file/bank/song's detail pane. Returns an HTML fragment (styled by
    `style.css` once embedded in the detail document) or '' when there is
    nothing worth warning about."""

    def __init__(
        self,
        template_engine: TemplateEngine,
        severity_presenter: SeverityPresenter,
    ):
        self._engine = template_engine
        self._presenter = severity_presenter

    def render(self, findings: list[Finding]) -> str:
        actionable = [f for f in findings if f.severity is not Severity.INFO]
        if not actionable:
            return ""

        worst = max((f.severity for f in actionable), key=lambda s: s.value)
        return self._engine.render(
            "diagnosis_banner.html",
            severity_class=self._presenter.css_class(worst),
            heading=self._presenter.heading(worst),
            messages=[f.message for f in actionable],
        )
