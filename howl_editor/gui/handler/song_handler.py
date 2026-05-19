# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QInputDialog

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.command import RemoveItemCommand, SwapBlobCommand
from howl_editor.gui.dialog.copy_target_dialog import (
    CopyTargetContainer, CopyTargetDialog,
)


class SongHandler:

    def __init__(self, window):
        self._w = window

    def add_song(self):
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self._w, "Add Song", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)")
        if not path:
            return

        self._w._editor.add_song(self._w.hwl, Path(path).read_bytes())
        self._w._mark_modified()
        self._w._rebuild_tree()
        self._w._notify(f"Added song {len(self._w.hwl.songs) - 1} from {Path(path).name}")

    def export_song(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self._w, f"Export Song {index}", f"song_{index}{FileFormatRegistry.CSEQ.extension}", FileFormatRegistry.CSEQ.file_filter)

        if path:
            Path(path).write_bytes(self._w.hwl.songs[index])
            self._w.status.showMessage(f"Exported song {index}")

    def export_song_as_midi(self, index: int):
        if not self._w.hwl or not self._w._midi_exporter:
            return

        path, _ = QFileDialog.getSaveFileName(
            self._w, f"Export Song {index} as MIDI", f"song_{index}{FileFormatRegistry.MIDI.extension}", FileFormatRegistry.MIDI.file_filter,
        )
        if not path:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[index])

            for i in range(len(cseq.songs)):
                if len(cseq.songs) > 1:
                    p = Path(path)
                    out = p.with_name(f"{p.stem}_seq{i}{p.suffix}")
                else:
                    out = Path(path)

                self._w._midi_exporter.export_to_file(cseq, out, i)

            self._w.status.showMessage(f"Exported song {index} as MIDI")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"MIDI export failed:\n{e}")

    def export_sequence_as_midi(self, song_index: int, seq_index: int):
        if not self._w.hwl or not self._w._midi_exporter:
            return

        path, _ = QFileDialog.getSaveFileName(
            self._w, f"Export Sequence {seq_index}",
            f"song_{song_index}_seq{seq_index}{FileFormatRegistry.MIDI.extension}", FileFormatRegistry.MIDI.file_filter,
        )
        if not path:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            self._w._midi_exporter.export_to_file(cseq, path, seq_index)
            self._w.status.showMessage(f"Exported sequence {seq_index} as MIDI")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"MIDI export failed:\n{e}")

    def replace_song(self, index: int):
        path, _ = QFileDialog.getOpenFileName(self._w, f"Replace Song {index}", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)")
        if not path:
            return

        self._w._undo_stack.push(
            SwapBlobCommand(self._w, f"Replace Song {index}", HowlCollection.SONGS, index, Path(path).read_bytes()),
        )
        self._w._notify(f"Replaced song {index} with {Path(path).name}")

    def remove_song(self, index: int):
        if QMessageBox.question(self._w, "Remove Song", f"Remove song {index}?") == QMessageBox.Yes:
            self._w._undo_stack.push(
                RemoveItemCommand(self._w, f"Remove Song {index}", HowlCollection.SONGS, index),
            )
            self._w._notify(f"Removed song {index}")

    def replace_sequence(self, song_index: int, seq_index: int):
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._w, "Select Source CSEQ", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)",
        )
        if not path:
            return

        try:
            source_cseq = self._w._cseq_reader.read(Path(path).read_bytes())
            source_seq_index = 0

            if len(source_cseq.songs) > 1:
                labels = [f"Sequence {i} (BPM={s.bpm}, {len(s.tracks)} tracks)"
                          for i, s in enumerate(source_cseq.songs)]
                label, ok = QInputDialog.getItem(
                    self._w, "Select Sequence", "Pick sequence from source:", labels, 0, False,
                )

                if not ok:
                    return

                source_seq_index = labels.index(label)

            new_blob = self._w._cseq_editor.replace_sequence(
                self._w.hwl.songs[song_index], seq_index, source_cseq.songs[source_seq_index],
            )
            self._w._undo_stack.push(
                SwapBlobCommand(self._w, f"Replace Sequence in Song {song_index}", HowlCollection.SONGS, song_index, new_blob),
            )
            self._w._notify(f"Replaced sequence {seq_index} in song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Replace failed:\n{e}")

    def add_sequence(self, song_index: int):
        """Append a sequence (from an external .cseq) onto an existing song."""
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._w, "Select Source CSEQ", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)",
        )
        if not path:
            return

        try:
            source_cseq = self._w._cseq_reader.read(Path(path).read_bytes())
            source_seq_index = 0

            if len(source_cseq.songs) > 1:
                labels = [f"Sequence {i} (BPM={s.bpm}, {len(s.tracks)} tracks)"
                          for i, s in enumerate(source_cseq.songs)]
                label, ok = QInputDialog.getItem(
                    self._w, "Select Sequence", "Pick sequence from source:", labels, 0, False,
                )

                if not ok:
                    return

                source_seq_index = labels.index(label)

            new_blob = self._w._cseq_editor.append_sequence(
                self._w.hwl.songs[song_index], source_cseq.songs[source_seq_index],
            )
            self._w._undo_stack.push(
                SwapBlobCommand(self._w, f"Add Sequence to Song {song_index}", HowlCollection.SONGS, song_index, new_blob),
            )
            self._w._notify(f"Added sequence to song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Add sequence failed:\n{e}")

    def copy_sequence(self, src_song: int, src_seq: int):
        """Copy a sequence into another song — either appended or replacing
        one of its existing sequences."""
        if not self._w.hwl:
            return

        try:
            src_cseq = self._w._cseq_reader.read(self._w.hwl.songs[src_song])

            if src_seq >= len(src_cseq.songs):
                return

            src_song_data = src_cseq.songs[src_seq]
            songs = self._build_copy_song_summaries()
            source_display = self._song_display(src_song)
            summary = (
                f"Copy sequence {src_seq} from {source_display} "
                f"(BPM={src_song_data.bpm}, {len(src_song_data.tracks)} tracks) to:"
            )
            dialog = CopyTargetDialog(
                self._w,
                title="Copy Sequence",
                prompt=summary,
                container_label="Target song:",
                child_label="Target sequence:",
                append_label="(Append as new sequence)",
                containers=songs,
                source_container_index=src_song,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            target = dialog.chosen_target()
            if target is None:
                return

            self._apply_sequence_copy(src_song_data, target.container_index, target.child_index)
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Copy failed:\n{e}")

    def _build_copy_song_summaries(self) -> list[CopyTargetContainer]:
        out: list[CopyTargetContainer] = []

        for i, blob in enumerate(self._w.hwl.songs):
            try:
                cseq = self._w._cseq_reader.read(blob)
                child_labels = tuple(
                    f"Sequence {slot} — BPM={s.bpm}, {len(s.tracks)} tracks"
                    for slot, s in enumerate(cseq.songs)
                )
            except Exception:
                child_labels = ()

            out.append(CopyTargetContainer(
                index=i, display=self._song_display(i), child_labels=child_labels,
            ))

        return out

    def _song_display(self, index: int) -> str:
        name = self._w._cseq_reader.get_name(index)
        return f"Song {index} — {name}" if name else f"Song {index}"

    def _apply_sequence_copy(self, src_song_data, target_song: int, target_seq: int | None) -> None:
        if target_seq is None:
            new_blob = self._w._cseq_editor.append_sequence(
                self._w.hwl.songs[target_song], src_song_data,
            )
            description = f"Copy sequence into Song {target_song}"
            message = f"Copied sequence as new entry in song {target_song}"
        else:
            new_blob = self._w._cseq_editor.replace_sequence(
                self._w.hwl.songs[target_song], target_seq, src_song_data,
            )
            description = f"Copy sequence over Song {target_song} sequence {target_seq}"
            message = f"Replaced sequence {target_seq} in song {target_song}"

        self._w._undo_stack.push(SwapBlobCommand(
            self._w, description, HowlCollection.SONGS, target_song, new_blob,
        ))
        self._w._notify(message)

    def remove_sequence(self, song_index: int, seq_index: int):
        if not self._w.hwl:
            return

        if QMessageBox.question(
            self._w, "Remove Sequence", f"Remove sequence {seq_index} from song {song_index}?",
        ) != QMessageBox.Yes:
            return

        try:
            new_blob = self._w._cseq_editor.remove_sequence(self._w.hwl.songs[song_index], seq_index)
            self._w._undo_stack.push(
                SwapBlobCommand(self._w, f"Remove Sequence {seq_index} from Song {song_index}", HowlCollection.SONGS, song_index, new_blob),
            )
            self._w._notify(f"Removed sequence {seq_index} from song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Remove failed:\n{e}")
