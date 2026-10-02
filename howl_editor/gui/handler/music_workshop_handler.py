# coding: utf-8

from PySide6.QtWidgets import QMessageBox

from howl_editor.export.exportable import ExportableContext, ExportableKind
from howl_editor.gui.dialog.track_events_dialog import TrackEventsDialog
from howl_editor.gui.handler.sequence_event_editor import SequenceEventEditor


class MusicWorkshopHandler:

    def __init__(self, window):
        self._w = window

    def audition(self, spu_index: int, pitch: int, label: str) -> None:
        if not self._w.hwl:
            return

        self._w._playback.play_spu_sample(spu_index, pitch, label)

    def play_sequence(self, song_index: int, seq_index: int) -> None:
        if not self._w.hwl:
            return

        self._w._playback.play_sequence(song_index, seq_index)

    def replace_sequence(self, song_index: int, seq_index: int) -> None:
        self._w._song_handler.replace_sequence(song_index, seq_index)

    def copy_sequence(self, song_index: int, seq_index: int) -> None:
        self._w._song_handler.copy_sequence(song_index, seq_index)

    def remove_sequence(self, song_index: int, seq_index: int) -> None:
        self._w._song_handler.remove_sequence(song_index, seq_index)

    def view_sequence_events(self, song_index: int, seq_index: int) -> None:
        if not self._w.hwl:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Cannot read song:\n{e}")
            return

        if seq_index >= len(cseq.songs):
            return

        song_name = self._w._cseq_reader.get_name(song_index)
        suffix = f" — {song_name}" if song_name else ""
        title = f"Song {song_index}{suffix} · Sequence {seq_index} events"
        TrackEventsDialog(
            self._w, title, cseq.songs[seq_index],
            editor=SequenceEventEditor(
                self._w._song_handler, song_index, seq_index,
            ),
            instrument_count=len(cseq.instruments),
            percussion_count=len(cseq.percussions),
        ).exec()

    def edit_instrument(self, song_index: int, inst_index: int) -> None:
        self._w._song_handler.edit_instrument(song_index, inst_index)

    def edit_percussion(self, song_index: int, perc_index: int) -> None:
        self._w._song_handler.edit_percussion(song_index, perc_index)

    def add_instrument(self, song_index: int) -> None:
        self._w._song_handler.add_instrument(song_index)

    def add_percussion(self, song_index: int) -> None:
        self._w._song_handler.add_percussion(song_index)

    def shift_instrument_octaves(self, song_index: int, inst_index: int, octaves: int) -> None:
        self._w._song_handler.shift_instrument_octaves(song_index, inst_index, octaves)

    def shift_percussion_octaves(self, song_index: int, perc_index: int, octaves: int) -> None:
        self._w._song_handler.shift_percussion_octaves(song_index, perc_index, octaves)

    def shift_selected_octaves(self, song_index: int, percussion: bool, indices, octaves: int) -> None:
        self._w._song_handler.shift_selected_octaves(song_index, percussion, indices, octaves)

    def set_selected_volume(self, song_index: int, percussion: bool, indices) -> None:
        self._w._song_handler.set_selected_volume(song_index, percussion, indices)

    def retarget_instrument(self, song_index: int, inst_index: int) -> None:
        self._w._song_handler.retarget_instrument(song_index, inst_index)

    def retarget_percussion(self, song_index: int, perc_index: int) -> None:
        self._w._song_handler.retarget_percussion(song_index, perc_index)

    def export_sequence(self, song_index: int, seq_index: int, label: str) -> None:
        self._w._export_handler.show_format_dialog(
            ExportableKind.SEQUENCE, label,
            ExportableContext(song_index=song_index, seq_index=seq_index),
        )

    def replace_sample(self, bank_index: int, sample_index: int) -> None:
        self._w._sample_handler.replace_sample(bank_index, sample_index)

    def copy_sample(self, bank_index: int, sample_index: int) -> None:
        self._w._sample_handler.copy_sample(bank_index, sample_index)

    def export_sample(self, bank_index: int, sample_index: int) -> None:
        self._w._sample_handler.export_sample(bank_index, sample_index)
