# coding: utf-8

import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog, QInputDialog

from howl_editor.gui.dialog.convert_midi_dialog import ConvertMidiDialog
from howl_editor.gui.dialog.saphi_export_dialog import SaphiExportDialog
from howl_editor.midi.converter import HAS_MIDO
from howl_editor.models import ScaFile, ScaMetadata
from howl_editor.sca.constants import SAPHI_BANK_MAX_SIZE


class ToolsHandler:

    def __init__(self, window):
        self._window = window

    def build_bank_from_vags(self):
        files, _ = QFileDialog.getOpenFileNames(self._window, "Select VAG Files", "", "VAG Files (*.vag);;All Files (*)")
        if not files:
            return

        try:
            spu_addrs = self._window.hwl.spu_addrs if self._window.hwl else []
            result = self._window._bank_builder.build_from_files(files, spu_addrs)

            if self._window.hwl and self._ask_store_in_hwl("bank"):
                self._window._editor.add_bank(self._window.hwl, result.bank_data)
                self._window._mark_modified()
                self._window._rebuild_tree()
                self._window._notify(f"Added bank {len(self._window.hwl.banks) - 1} with {len(files)} samples")
            else:
                path, _ = QFileDialog.getSaveFileName(self._window, "Save Bank", "bank.bnk", "Bank Files (*.bnk)")
                if path:
                    Path(path).write_bytes(result.bank_data)
                    self._window._notify(f"Saved bank to {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Failed:\n{e}\n{traceback.format_exc()}")

    def midi_to_cseq(self):
        if not HAS_MIDO:
            return

        path, _ = QFileDialog.getOpenFileName(self._window, "Select MIDI", "", "MIDI Files (*.mid *.midi)")
        if not path:
            return

        try:
            info = self._window._midi_converter.get_midi_info(path)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Cannot read MIDI:\n{e}")
            return

        max_spu = len(self._window.hwl.spu_addrs) if self._window.hwl else 0
        dialog = ConvertMidiDialog(self._window, info, max_spu)
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            cseq_data = self._window._midi_converter.convert(path, dialog.get_settings())

            if self._window.hwl and self._ask_store_in_hwl("song"):
                self._window._editor.add_song(self._window.hwl, cseq_data)
                self._window._mark_modified()
                self._window._rebuild_tree()
                self._window._notify(f"Added song {len(self._window.hwl.songs) - 1}")
            else:
                save_path, _ = QFileDialog.getSaveFileName(self._window, "Save CSEQ", "song.cseq", "CSEQ Files (*.cseq)")
                if save_path:
                    Path(save_path).write_bytes(cseq_data)
                    self._window._notify(f"Saved CSEQ to {Path(save_path).name}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Conversion failed:\n{e}")

    def validate_bank_song(self):
        if not self._window.hwl or not self._window._validator:
            return

        bank_indices = list(range(len(self._window.hwl.banks)))
        bank_labels = [self._window._get_item_label("Bank", i, self._window._bank_reader.get_name(i)) for i in bank_indices]
        bank_label, ok = QInputDialog.getItem(self._window, "Validate", "Select bank:", bank_labels, 0, False)

        if not ok:
            return

        song_indices = list(range(len(self._window.hwl.songs)))
        song_labels = [self._window._get_item_label("Song", i, self._window._cseq_reader.get_name(i)) for i in song_indices]
        song_label, ok = QInputDialog.getItem(self._window, "Validate", "Select song:", song_labels, 0, False)

        if not ok:
            return

        bank_idx = bank_indices[bank_labels.index(bank_label)]
        song_idx = song_indices[song_labels.index(song_label)]

        try:
            result = self._window._validator.validate(
                self._window.hwl.banks[bank_idx], self._window.hwl.songs[song_idx], self._window.hwl.spu_addrs,
            )
            QMessageBox.information(self._window, "Validation Result", result.message)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Validation failed:\n{e}")

    def export_for_saphi(self):
        if not self._window.hwl:
            return

        if not self._window.hwl.banks or not self._window.hwl.songs:
            QMessageBox.information(self._window, "Export for Saphi","The current HWL has no banks or songs to export.")
            return

        bank_labels = [self._window._get_item_label("Bank", i, self._window._bank_reader.get_name(i)) for i in range(len(self._window.hwl.banks))]
        song_labels = [self._window._get_item_label("Song", i, self._window._cseq_reader.get_name(i)) for i in range(len(self._window.hwl.songs))]
        bank_sizes = [len(b) for b in self._window.hwl.banks]

        dialog = SaphiExportDialog(self._window, bank_labels, song_labels, bank_sizes, SAPHI_BANK_MAX_SIZE)
        if dialog.exec() != QDialog.Accepted:
            return

        selection = dialog.get_selection()
        path, _ = QFileDialog.getSaveFileName(
            self._window, "Save Saphi Export",
            f"{selection.name}.sca", "Saphi Audio (*.sca)",
        )

        if not path:
            return

        try:
            bank = self._window.hwl.banks[selection.bank_index]
            cseq = self._window.hwl.songs[selection.song_index]
            sample_sizes = self._window._sample_sizes_extractor.extract(bank, self._window.hwl.spu_addrs)

            sca = ScaFile(
                bank=bank,
                cseq=cseq,
                sample_sizes=sample_sizes,
                metadata=ScaMetadata(name=selection.name, author=selection.author),
            )

            blob = self._window._sca_writer.serialize(sca)
            Path(path).write_bytes(blob)
            self._window.status.showMessage(f"Exported {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Saphi export failed:\n{e}\n{traceback.format_exc()}")

    def import_saphi(self):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Import Saphi Audio Container", "", "Saphi Audio (*.sca);;All Files (*)",
        )
        if not path:
            return

        try:
            sca = self._window._sca_reader.parse(Path(path).read_bytes())
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Failed to parse .sca file:\n{e}")
            return

        bank_index = self._window._editor.add_bank(self._window.hwl, sca.bank)
        song_index = self._window._editor.add_song(self._window.hwl, sca.cseq)
        self._window._mark_modified()
        self._window._rebuild_tree()
        self._window._notify(
            f"Imported \"{sca.metadata.name}\" by {sca.metadata.author} "
            f"(bank {bank_index}, song {song_index})"
        )

    def batch_export(self):
        if not self._window.hwl or not self._window._batch_exporter:
            return

        folder = QFileDialog.getExistingDirectory(self._window, "Batch Export - Select Output Folder")
        if not folder:
            return

        try:
            self._window.status.showMessage("Batch exporting...")
            QApplication.processEvents()
            result = self._window._batch_exporter.export(self._window.hwl, Path(folder))
            QMessageBox.information(
                self._window, "Batch Export Complete",
                f"Exported:\n"
                f"  {result.banks} Banks\n"
                f"  {result.songs} Songs\n"
                f"  {result.midis} MIDI files\n"
                f"  {result.samples} Samples (VAG + WAV)",
            )
            self._window.status.showMessage("Batch export complete")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Batch export failed:\n{e}")

    def _ask_store_in_hwl(self, item_type: str) -> bool:
        return QMessageBox.question(
            self._window, "Add to HWL?",
            f"Add {item_type} to the loaded HWL file?\n\nSelect No to save as a standalone file instead.",
        ) == QMessageBox.Yes
