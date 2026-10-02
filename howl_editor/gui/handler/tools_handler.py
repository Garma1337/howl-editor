# coding: utf-8

import traceback
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QInputDialog

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotLimitError
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.dialog.convert_midi_dialog import ConvertMidiDialog
from howl_editor.gui.dialog.diagnosis_report_dialog import DiagnosisReportDialog
from howl_editor.gui.dialog.saphi_export_dialog import SaphiExportDialog
from howl_editor.midi.availability import HAS_MIDO
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE
from howl_editor.saphi.formats.sca.models import ScaFile, ScaMetadata


class ToolsHandler:

    def __init__(self, window):
        self._window = window

    def build_bank_from_vags(self):
        files, _ = QFileDialog.getOpenFileNames(self._window, "Select VAG Files", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)")
        if not files:
            return

        try:
            if self._window.hwl:
                spu_addrs = self._window.hwl.spu_addrs
                indices = self._window._services.resolve("spu_slot_allocator").allocate(self._window.hwl, len(files))
            else:
                spu_addrs, indices = [], None

            spu_before = list(spu_addrs)
            result = self._window._services.resolve("bank_builder").build_from_files(files, spu_addrs, indices)

            if self._window.hwl and self._ask_store_in_hwl("bank"):
                self._window._services.resolve("howl_editor").add_bank(self._window.hwl, result.bank_data)

                for spu_index, sample_rate in zip(result.new_spu_indices, result.sample_rates):
                    self._window._services.resolve("howl_editor").attach_sample_rate(self._window.hwl, spu_index, sample_rate)

                self._window._mark_modified()
                self._window._rebuild_tree()
                self._window._notify(f"Added bank {len(self._window.hwl.banks) - 1} with {len(files)} samples")
            else:
                # The builder wrote the new sizes straight into the live table;
                # a bank that only goes to disc must leave the HWL untouched.
                if self._window.hwl:
                    self._window.hwl.spu_addrs[:] = spu_before

                path, _ = QFileDialog.getSaveFileName(self._window, "Save Bank", f"bank{FileFormatRegistry.BANK.extension}", FileFormatRegistry.BANK.file_filter)

                if path:
                    Path(path).write_bytes(result.bank_data)
                    self._window._notify(f"Saved bank to {Path(path).name}")
        except SpuSlotLimitError as e:
            QMessageBox.warning(self._window, "SPU Slot Limit", str(e))
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Failed:\n{e}\n{traceback.format_exc()}")

    def midi_to_cseq(self):
        if not HAS_MIDO:
            return

        path, _ = QFileDialog.getOpenFileName(self._window, "Select MIDI", "", FileFormatRegistry.MIDI.file_filter)
        if not path:
            return

        try:
            info = self._window._services.resolve("midi_converter").get_midi_info(path)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Cannot read MIDI:\n{e}")
            return

        max_spu = len(self._window.hwl.spu_addrs) if self._window.hwl else 0
        free = self._window._services.resolve("spu_slot_usage").free_slots(self._window.hwl) if self._window.hwl else None
        dialog = ConvertMidiDialog(
            self._window, info, max_spu, self._window._services.resolve("gm_drum_names"), free_spu_indices=free,
            pitch_headroom=self._window._services.resolve("pitch_headroom_inspector"),
            pitch_stepper=self._window._services.resolve("pitch_stepper"),
        )
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            cseq_data = self._window._services.resolve("midi_converter").convert(path, dialog.get_settings())

            guard = self._window._services.resolve("cseq_size_guard")
            if guard is not None and not self._window.confirm_within_limit(guard.check(cseq_data)):
                return

            if self._window.hwl and self._ask_store_in_hwl("song"):
                self._window._services.resolve("howl_editor").add_song(self._window.hwl, cseq_data)
                self._window._mark_modified()
                self._window._rebuild_tree()
                self._window._notify(f"Added song {len(self._window.hwl.songs) - 1}")
            else:
                save_path, _ = QFileDialog.getSaveFileName(self._window, "Save CSEQ", f"song{FileFormatRegistry.CSEQ.extension}", FileFormatRegistry.CSEQ.file_filter)

                if save_path:
                    Path(save_path).write_bytes(cseq_data)
                    self._window._notify(f"Saved CSEQ to {Path(save_path).name}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Conversion failed:\n{e}")

    def validate_bank_song(self):
        if not self._window.hwl or not self._window._services.resolve("validator"):
            return

        bank_indices = list(range(len(self._window.hwl.banks)))
        bank_labels = [self._window._get_item_label("Bank", i, self._window._services.resolve("bank_reader").get_name(i)) for i in bank_indices]
        bank_label, ok = QInputDialog.getItem(self._window, "Validate", "Select bank:", bank_labels, 0, False)

        if not ok:
            return

        song_indices = list(range(len(self._window.hwl.songs)))
        song_labels = [self._window._get_item_label("Song", i, self._window._services.resolve("cseq_reader").get_name(i)) for i in song_indices]
        song_label, ok = QInputDialog.getItem(self._window, "Validate", "Select song:", song_labels, 0, False)

        if not ok:
            return

        bank_idx = bank_indices[bank_labels.index(bank_label)]
        song_idx = song_indices[song_labels.index(song_label)]

        try:
            result = self._window._services.resolve("validator").validate(
                self._window.hwl.banks[bank_idx], self._window.hwl.songs[song_idx], self._window.hwl.spu_addrs,
            )
            self._show_validation_result(result)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Validation failed:\n{e}")

    def _show_validation_result(self, result) -> None:
        """A report the user asked for, listing every missing sample — it is
        read, not glanced at, so it waits in a dialog instead of fading from
        the notification bar."""
        box = QMessageBox(self._window)
        box.setIcon(QMessageBox.Information if result.valid else QMessageBox.Warning)
        box.setWindowTitle("Validation Result")
        box.setText(result.message)
        box.exec()

    def export_for_saphi(self):
        if not self._window.hwl:
            return

        if not self._window.hwl.banks or not self._window.hwl.songs:
            self._window._notify_warning("The current HWL has no banks or songs to export.")
            return

        bank_labels = [self._window._get_item_label("Bank", i, self._window._services.resolve("bank_reader").get_name(i)) for i in range(len(self._window.hwl.banks))]
        song_labels = [self._window._get_item_label("Song", i, self._window._services.resolve("cseq_reader").get_name(i)) for i in range(len(self._window.hwl.songs))]
        bank_sizes = [len(b) for b in self._window.hwl.banks]

        dialog = SaphiExportDialog(self._window, bank_labels, song_labels, bank_sizes, SAPHI_BANK_MAX_SIZE)
        if dialog.exec() != QDialog.Accepted:
            return

        selection = dialog.get_selection()
        if not self._export_slots_within_stock_table(selection):
            return

        path, _ = QFileDialog.getSaveFileName(
            self._window, "Save Saphi Export",
            f"{selection.name}{FileFormatRegistry.SCA.extension}", FileFormatRegistry.SCA.file_filter,
        )

        if not path:
            return

        try:
            bank = self._window.hwl.banks[selection.bank_index]
            cseq = self._window.hwl.songs[selection.song_index]
            sample_sizes = self._window._services.resolve("sample_sizes_extractor").extract(bank, self._window.hwl.spu_addrs)

            sca = ScaFile(
                bank=bank,
                cseq=cseq,
                sample_sizes=sample_sizes,
                metadata=ScaMetadata(name=selection.name, author=selection.author),
            )

            blob = self._window._services.resolve("sca_writer").serialize(sca)
            Path(path).write_bytes(blob)
            self._window._notify(f"Exported {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Saphi export failed:\n{e}\n{traceback.format_exc()}")

    def import_saphi(self):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Import Saphi Audio Container", "", f"{FileFormatRegistry.SCA.file_filter};;All Files (*)",
        )
        
        if not path:
            return

        try:
            sca = self._window._services.resolve("sca_reader").parse(Path(path).read_bytes())
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Failed to parse .sca file:\n{e}")
            return

        song_guard = self._window._services.resolve("cseq_size_guard")
        if song_guard is not None and not self._window.confirm_within_limit(song_guard.check(sca.cseq)):
            return

        bank_guard = self._window._services.resolve("bank_size_guard")
        if bank_guard is not None and not self._window.confirm_within_limit(
            bank_guard.check(self._window.hwl, len(self._window.hwl.banks), sca.bank),
        ):
            return

        bank_index = self._window._services.resolve("howl_editor").add_bank(self._window.hwl, sca.bank)
        song_index = self._window._services.resolve("howl_editor").add_song(self._window.hwl, sca.cseq)
        self._window._mark_modified()
        self._window._rebuild_tree()
        self._window._notify(
            f"Imported \"{sca.metadata.name}\" by {sca.metadata.author} "
            f"(bank {bank_index}, song {song_index})"
        )

    def batch_export(self):
        if not self._window.hwl or not self._window._services.resolve("batch_exporter"):
            return

        folder = QFileDialog.getExistingDirectory(self._window, "Batch Export - Select Output Folder")
        if not folder:
            return

        # The export runs on a worker thread while the window stays editable.
        # Blobs are immutable, so copying the lists is enough to keep what is
        # being written from shifting under it.
        hwl = replace(
            self._window.hwl,
            banks=list(self._window.hwl.banks),
            songs=list(self._window.hwl.songs),
            spu_addrs=list(self._window.hwl.spu_addrs),
        )
        rate = self._window._services.resolve("vag_rate_provider").rate
        busy = self._window.notifications.push_busy(
            f"Exporting everything to {Path(folder).name}…",
        )
        handle = self._window._services.resolve("tasks").run(
            lambda progress: self._window._services.resolve("batch_exporter").export(
                hwl, Path(folder), rate, progress=progress,
            ),
            lambda result: busy.succeeded(
                f"Batch export complete: {result.banks} banks, {result.songs} songs, "
                f"{result.midis} MIDI files, {result.samples} samples"
            ),
            on_error=lambda message: busy.failed(f"Batch export failed: {message}"),
            on_cancelled=lambda: busy.succeeded("Batch export cancelled — partial files kept"),
            on_progress=busy.set_progress,
        )
        busy.set_cancel(handle.cancel)

    def diagnose_howl(self):
        """Run the whole-file engine-limit sweep and show the report."""
        if not self._window.hwl or self._window._services.resolve("howl_diagnostics") is None:
            return

        try:
            data = self._window._services.resolve("howl_writer").serialize(self._window.hwl)
            report = self._window._services.resolve("howl_diagnostics").diagnose(
                self._window.hwl,
                howl_file_size=len(data),
                iso_budget_bytes=self._window._original_howl_size,
            )
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Diagnosis failed:\n{e}")
            return

        DiagnosisReportDialog(
            self._window, report, self._window._services.resolve("severity_presenter"),
        ).exec()

    def _export_slots_within_stock_table(self, selection) -> bool:
        """Refuse an export whose bank or song uses SPU slots Saphi cannot load."""
        bank = self._window.hwl.banks[selection.bank_index]
        cseq = self._window.hwl.songs[selection.song_index]

        try:
            blocked = self._window._services.resolve("sca_spu_slot_validator").out_of_range_slots(bank, cseq)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Saphi export failed:\n{e}")
            return False

        if not blocked:
            return True

        QMessageBox.warning(
            self._window, "Export for Saphi",
            f"This export uses SPU slot(s) {', '.join(map(str, blocked))}, but Saphi only supports "
            f"slots 0-{constants.MAX_SPU_SLOTS - 1}.\n\n"
            f"Saphi loads custom music against the stock game's {constants.MAX_SPU_SLOTS}-slot table. "
            f"Higher slots overwrite sound effects in memory (e.g. the pause menu sounds) and "
            f"the instruments using them play silence.\n\n"
            f"Move these samples onto existing slots below {constants.MAX_SPU_SLOTS} and export again.",
        )
        return False

    def _ask_store_in_hwl(self, item_type: str) -> bool:
        return QMessageBox.question(
            self._window, "Add to HWL?",
            f"Add {item_type} to the loaded HWL file?\n\nSelect No to save as a standalone file instead.",
        ) == QMessageBox.Yes
