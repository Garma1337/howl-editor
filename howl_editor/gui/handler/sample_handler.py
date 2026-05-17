# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from howl_editor.gui.command import SwapBlobCommand
from howl_editor.models import VagSample
from howl_editor.sca.constants import SAPHI_BANK_MAX_SIZE


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
            self._window._editor.attach_sample_rate(self._window.hwl, spu_index, vag.sample_rate)
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

            if not self._confirm_size_change(bank_index, sample_index, len(vag.data)):
                return

            spu_index = self._find_spu_index(bank_index, sample_index)
            new_blob = self._window._bank_builder.replace_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, vag.data, self._window._bank_reader,
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Replace Sample in Bank {bank_index}", "banks", bank_index, new_blob, snapshot_spu=True),
            )

            if spu_index is not None:
                self._propagate_sample_rate_to_fx(spu_index, vag.sample_rate)

            self._window._notify(f"Replaced sample {sample_index} in bank {bank_index}")
            self._warn_if_bank_oversized(bank_index, len(new_blob))
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Replace failed:\n{e}")

    def _find_spu_index(self, bank_index: int, sample_index: int) -> int | None:
        try:
            samples = self._window._bank_reader.parse(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
            )

            if 0 <= sample_index < len(samples):
                return samples[sample_index].spu_index
        except Exception:
            pass

        return None

    def _propagate_sample_rate_to_fx(self, spu_index: int, sample_rate: int) -> None:
        if sample_rate <= 0:
            return

        pitch = int(round(sample_rate / 44100.0 * 4096.0))
        for fx in self._window.hwl.other_fx:
            if fx.spu_index == spu_index:
                fx.pitch = pitch

    def _confirm_size_change(self, bank_index: int, sample_index: int, new_data_len: int) -> bool:
        samples = self._window._bank_reader.parse(
            self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
        )

        if sample_index >= len(samples):
            return True

        old_data_len = len(samples[sample_index].data)
        if new_data_len == old_data_len:
            return True

        delta = new_data_len - old_data_len
        if new_data_len > old_data_len:
            return QMessageBox.warning(
                self._window, "Sample is larger than original",
                f"The new sample is {new_data_len} bytes — {delta} bytes LARGER "
                f"than the original ({old_data_len} bytes).\n\n"
                f"This will increase the bank's SPU footprint and may push the bank "
                f"past Saphi's {SAPHI_BANK_MAX_SIZE}-byte limit. Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            ) == QMessageBox.Yes

        QMessageBox.information(
            self._window, "Sample size differs",
            f"The new sample is {-delta} bytes SMALLER than the original "
            f"({old_data_len} bytes → {new_data_len} bytes).",
        )

        return True

    def _warn_if_bank_oversized(self, bank_index: int, bank_size: int) -> None:
        if bank_size <= SAPHI_BANK_MAX_SIZE:
            return

        over_by = bank_size - SAPHI_BANK_MAX_SIZE
        self._window.status.showMessage(
            f"⚠ Bank {bank_index} is {bank_size} bytes — {over_by} over the "
            f"Saphi {SAPHI_BANK_MAX_SIZE}-byte limit. Saphi will reject the export.",
            10000,
        )

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
