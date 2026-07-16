# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QInputDialog

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.command import RemoveItemCommand, SwapBlobCommand
from howl_editor.gui.dialog.merge_bank_dialog import MergeBankDialog
from howl_editor.ps1.formats.vag.models import VagSample


class BankHandler:

    def __init__(self, window):
        self._window = window

    def _bank_within_limit(self, index: int, blob) -> bool:
        """Gate a prospective bank blob through the SPU-residency guard, warning
        (with override) if the bank's worst-case race no longer fits SPU RAM."""
        guard = self._window._bank_size_guard
        return guard is None or self._window.confirm_within_limit(
            guard.check(self._window.hwl, index, blob),
        )

    def add_bank(self):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self._window, "Add Bank", "", f"{FileFormatRegistry.BANK.file_filter};;All Files (*)")
        if not path:
            return

        data = Path(path).read_bytes()
        if not self._bank_within_limit(len(self._window.hwl.banks), data):
            return

        self._window._editor.add_bank(self._window.hwl, data)
        self._window._mark_modified()
        self._window._rebuild_tree()
        self._window._notify(f"Added bank from {Path(path).name}")

    def export_bank(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self._window, f"Export Bank {index}", f"bank_{index}{FileFormatRegistry.BANK.extension}", FileFormatRegistry.BANK.file_filter)
        if path:
            Path(path).write_bytes(self._window.hwl.banks[index])
            self._window.status.showMessage(f"Exported bank {index}")

    def export_bank_samples(self, index: int):
        folder = QFileDialog.getExistingDirectory(self._window, f"Export Samples from Bank {index}")
        if not folder:
            return

        try:
            samples = self._window._bank_reader.parse(self._window.hwl.banks[index], self._window.hwl.spu_addrs)

            for sample in samples:
                self._window._vag_writer.write_file(
                    VagSample(data=sample.data),
                    Path(folder) / f"sample_{sample.spu_index}.vag",
                )

            self._window.status.showMessage(f"Exported {len(samples)} samples from bank {index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def export_bank_samples_as_wav(self, index: int):
        if not self._window.hwl:
            return

        folder = QFileDialog.getExistingDirectory(self._window, f"Export WAVs from Bank {index}")
        if not folder:
            return

        try:
            samples = self._window._bank_reader.parse(self._window.hwl.banks[index], self._window.hwl.spu_addrs)
            rate = self._window._vag_rate.rate

            for sample in samples:
                wav = self._window._vag_decoder.decode_to_wav(sample.data, rate)
                (Path(folder) / f"sample_{sample.spu_index}.wav").write_bytes(wav)

            self._window.status.showMessage(f"Exported {len(samples)} WAVs from bank {index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def merge_bank(self, index: int):
        if not self._window.hwl or len(self._window.hwl.banks) < 2:
            QMessageBox.information(self._window, "Merge Bank", "Need at least two banks to merge.")
            return

        bank_indices = [i for i in range(len(self._window.hwl.banks)) if i != index]
        bank_labels = [self._window._get_item_label("Bank", i, self._window._bank_reader.get_name(i)) for i in bank_indices]

        label, ok = QInputDialog.getItem(
            self._window, "Select Source Bank", f"Merge into Bank {index} from:", bank_labels, 0, False,
        )

        if not ok:
            return

        source_index = bank_indices[bank_labels.index(label)]

        try:
            target_samples = self._window._bank_reader.parse(self._window.hwl.banks[index], self._window.hwl.spu_addrs)
            source_samples = self._window._bank_reader.parse(self._window.hwl.banks[source_index], self._window.hwl.spu_addrs)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Failed to parse banks:\n{e}")
            return

        dialog = MergeBankDialog(
            self._window, target_samples, source_samples, self._window.hwl.spu_addrs,
            target_label=f"Bank {index}", source_label=f"Bank {source_index}",
        )

        if dialog.exec() != QDialog.Accepted:
            return

        result = dialog.get_result()
        new_blob = self._window._bank_builder.merge(result)

        if not self._bank_within_limit(index, new_blob):
            return

        self._window._undo_stack.push(
            SwapBlobCommand(self._window, f"Merge into Bank {index}", HowlCollection.BANKS, index, new_blob),
        )

        self._window._notify(f"Merged {len(result)} samples into bank {index}")

    def replace_bank(self, index: int):
        path, _ = QFileDialog.getOpenFileName(self._window, f"Replace Bank {index}", "", f"{FileFormatRegistry.BANK.file_filter};;All Files (*)")
        if not path:
            return

        data = Path(path).read_bytes()
        if not self._bank_within_limit(index, data):
            return

        self._window._undo_stack.push(
            SwapBlobCommand(self._window, f"Replace Bank {index}", HowlCollection.BANKS, index, data),
        )

        self._window._notify(f"Replaced bank {index} with {Path(path).name}")

    def remove_bank(self, index: int):
        if QMessageBox.question(self._window, "Remove Bank", f"Remove bank {index}?") == QMessageBox.Yes:
            self._window._undo_stack.push(
                RemoveItemCommand(self._window, f"Remove Bank {index}", HowlCollection.BANKS, index),
            )

            self._window._notify(f"Removed bank {index}")
