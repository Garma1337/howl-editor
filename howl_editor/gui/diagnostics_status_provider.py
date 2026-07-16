# coding: utf-8

from howl_editor.ctr.diagnostics.diagnostics_index import DiagnosticsIndex
from howl_editor.ctr.diagnostics.howl_diagnostics import HowlDiagnostics
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr.formats.howl.writer import HowlWriter


class DiagnosticsStatusProvider:
    """Builds a `DiagnosticsIndex` for the current file state, so the GUI can
    badge banks / songs / the file that break an engine limit. Serializes the
    file to measure its true on-disc size for the ISO-budget check."""

    def __init__(self, diagnostics: HowlDiagnostics, writer: HowlWriter):
        self._diagnostics = diagnostics
        self._writer = writer

    def index_for(
        self, hwl: HowlFile, original_howl_size: int | None,
    ) -> DiagnosticsIndex:
        # serialized_size runs the layout math only — no ~file-sized buffer is
        # built, since this runs on every tree rebuild (after every edit).
        report = self._diagnostics.diagnose(
            hwl,
            howl_file_size=self._writer.serialized_size(hwl),
            iso_budget_bytes=original_howl_size,
        )
        return DiagnosticsIndex(report)
