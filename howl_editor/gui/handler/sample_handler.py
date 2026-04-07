# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from howl_editor.gui.command import SwapBlobCommand
from howl_editor.models import VagSample


class SampleHandler:

    def __init__(self, window):
        self._window = window

    def export_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._bank_reader.parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export Sample SPU {sample.spu_index}",
                f"sample_{sample.spu_index}.vag", "VAG Files (*.vag)",
            )

            if path:
                self._window._vag_writer.write_file(VagSample(data=sample.data), path)
                self._window.status.showMessage(f"Exported SPU {sample.spu_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def export_sample_as_wav(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._bank_reader.parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export WAV SPU {sample.spu_index}",
                f"sample_{sample.spu_index}.wav", "WAV Files (*.wav)",
            )

            if path:
                wav = self._window._vag_decoder.decode_to_wav(sample.data)
                Path(path).write_bytes(wav)
                self._window.status.showMessage(f"Exported SPU {sample.spu_index} as WAV")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def add_sample(self, bank_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Add Sample to Bank", "", "VAG Files (*.vag);;All Files (*)",
        )
        if not path:
            return

        try:
            vag = self._window._vag_reader.read_file(path)
            new_blob = self._window._bank_builder.add_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                vag.data, self._window._bank_reader,
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Add Sample to Bank {bank_index}", "banks", bank_index, new_blob, snapshot_spu=True),
            )
            spu_index = len(self._window.hwl.spu_addrs) - 1
            self._window._notify(f"Added sample SPU {spu_index} to bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Add sample failed:\n{e}")

    def replace_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Replace Sample", "", "VAG Files (*.vag);;All Files (*)",
        )
        if not path:
            return

        try:
            vag = self._window._vag_reader.read_file(path)
            new_blob = self._window._bank_builder.replace_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, vag.data, self._window._bank_reader,
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Replace Sample in Bank {bank_index}", "banks", bank_index, new_blob, snapshot_spu=True),
            )
            self._window._notify(f"Replaced sample {sample_index} in bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Replace failed:\n{e}")

    def remove_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        if QMessageBox.question(
            self._window, "Remove Sample", f"Remove sample {sample_index} from bank {bank_index}?",
        ) != QMessageBox.Yes:
            return

        try:
            new_blob = self._window._bank_builder.remove_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, self._window._bank_reader,
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Remove Sample {sample_index} from Bank {bank_index}", "banks", bank_index, new_blob, snapshot_spu=True),
            )
            self._window._notify(f"Removed sample {sample_index} from bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Remove failed:\n{e}")
