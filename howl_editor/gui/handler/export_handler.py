# coding: utf-8

from PySide6.QtWidgets import QDialog

from howl_editor.export.exportable import ExportableContext, ExportableKind
from howl_editor.file_format_registry import FileFormat, FileFormatRegistry
from howl_editor.gui.dialog.export_dialog import ExportDialog
from howl_editor.midi.converter import HAS_MIDO

_OPTIONS: dict[ExportableKind, list[FileFormat]] = {
    ExportableKind.BANK: [FileFormatRegistry.BANK],
    ExportableKind.SAMPLE: [FileFormatRegistry.WAV, FileFormatRegistry.VAG],
    ExportableKind.SONG: [FileFormatRegistry.CSEQ, FileFormatRegistry.MIDI],
    ExportableKind.SEQUENCE: [FileFormatRegistry.MIDI],
}


class ExportHandler:

    def __init__(self, window):
        self._w = window

    def show_format_dialog(
        self, kind: ExportableKind, name: str, ctx: ExportableContext,
    ) -> None:
        options = self.options(kind)
        if not options:
            return

        if len(options) == 1:
            self._dispatch(kind, options[0], ctx)
            return

        dialog = ExportDialog(self._w, name, options)
        if dialog.exec() != QDialog.Accepted:
            return

        chosen = dialog.chosen_format()
        if chosen is not None:
            self._dispatch(kind, chosen, ctx)

    def options(self, kind: ExportableKind) -> list[FileFormat]:
        """Filter the static option list by runtime capability (e.g. MIDI
        export requires the optional `mido` library)."""
        result: list[FileFormat] = []

        for fmt in _OPTIONS.get(kind, []):
            if fmt is FileFormatRegistry.MIDI and not HAS_MIDO:
                continue

            result.append(fmt)

        return result

    def _dispatch(
        self, kind: ExportableKind, fmt: FileFormat, ctx: ExportableContext,
    ) -> None:
        if kind == ExportableKind.BANK and fmt is FileFormatRegistry.BANK:
            self._w._bank_handler.export_bank(ctx.bank_index)
            return

        if kind == ExportableKind.SAMPLE and fmt is FileFormatRegistry.WAV:
            self._w._sample_handler.export_sample_as_wav(ctx.bank_index, ctx.sample_index)
            return

        if kind == ExportableKind.SAMPLE and fmt is FileFormatRegistry.VAG:
            self._w._sample_handler.export_sample(ctx.bank_index, ctx.sample_index)
            return

        if kind == ExportableKind.SONG and fmt is FileFormatRegistry.CSEQ:
            self._w._song_handler.export_song(ctx.song_index)
            return

        if kind == ExportableKind.SONG and fmt is FileFormatRegistry.MIDI:
            self._w._song_handler.export_song_as_midi(ctx.song_index)
            return

        if kind == ExportableKind.SEQUENCE and fmt is FileFormatRegistry.MIDI:
            self._w._song_handler.export_sequence_as_midi(ctx.song_index, ctx.seq_index)
            return
