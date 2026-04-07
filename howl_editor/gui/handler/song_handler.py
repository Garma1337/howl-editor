# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from howl_editor.gui.command import RemoveItemCommand, SwapBlobCommand


class SongHandler:

    def __init__(self, window):
        self._w = window

    def add_song(self):
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self._w, "Add Song", "", "CSEQ Files (*.cseq);;All Files (*)")
        if not path:
            return

        self._w._editor.add_song(self._w.hwl, Path(path).read_bytes())
        self._w._mark_modified()
        self._w._rebuild_tree()
        self._w._notify(f"Added song {len(self._w.hwl.songs) - 1} from {Path(path).name}")

    def export_song(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self._w, f"Export Song {index}", f"song_{index}.cseq", "CSEQ Files (*.cseq)")

        if path:
            Path(path).write_bytes(self._w.hwl.songs[index])
            self._w.status.showMessage(f"Exported song {index}")

    def export_song_as_midi(self, index: int):
        if not self._w.hwl or not self._w._midi_exporter:
            return

        path, _ = QFileDialog.getSaveFileName(
            self._w, f"Export Song {index} as MIDI", f"song_{index}.mid", "MIDI Files (*.mid)",
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
            f"song_{song_index}_seq{seq_index}.mid", "MIDI Files (*.mid)",
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
        path, _ = QFileDialog.getOpenFileName(self._w, f"Replace Song {index}", "", "CSEQ Files (*.cseq);;All Files (*)")
        if not path:
            return

        self._w._undo_stack.push(
            SwapBlobCommand(self._w, f"Replace Song {index}", "songs", index, Path(path).read_bytes()),
        )
        self._w._notify(f"Replaced song {index} with {Path(path).name}")

    def remove_song(self, index: int):
        if QMessageBox.question(self._w, "Remove Song", f"Remove song {index}?") == QMessageBox.Yes:
            self._w._undo_stack.push(
                RemoveItemCommand(self._w, f"Remove Song {index}", "songs", index),
            )
            self._w._notify(f"Removed song {index}")

    def replace_sequence(self, song_index: int, seq_index: int):
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._w, "Select Source CSEQ", "", "CSEQ Files (*.cseq);;All Files (*)",
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
                SwapBlobCommand(self._w, f"Replace Sequence in Song {song_index}", "songs", song_index, new_blob),
            )
            self._w._notify(f"Replaced sequence {seq_index} in song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Replace failed:\n{e}")

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
                SwapBlobCommand(self._w, f"Remove Sequence {seq_index} from Song {song_index}", "songs", song_index, new_blob),
            )
            self._w._notify(f"Removed sequence {seq_index} from song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Remove failed:\n{e}")
