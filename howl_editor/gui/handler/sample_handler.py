# coding: utf-8

from enum import Enum
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.command import SwapBlobCommand
from howl_editor.gui.dialog.copy_target_dialog import (
    CopyTargetContainer, CopyTargetDialog,
)
from howl_editor.ps1 import spu
from howl_editor.ps1.formats.vag.models import VagSample
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE


class SharedChoice(Enum):
    """What to do about the other banks claiming the sample being replaced."""
    ALONE = "alone"            # nothing else claims it — no question to ask
    UPDATE_ALL = "update_all"
    THIS_ONLY = "this_only"
    CANCEL = "cancel"


class SampleHandler:

    def __init__(self, window):
        self._window = window

    def _bank_within_limit(self, index: int, blob) -> bool:
        """Gate a prospective bank blob through the SPU-residency guard, warning
        (with override) if the bank's worst-case race no longer fits SPU RAM."""
        guard = self._window._bank_size_guard
        return guard is None or self._window.confirm_within_limit(
            guard.check(self._window.hwl, index, blob),
        )

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
                f"sample_{sample.spu_index}{FileFormatRegistry.VAG.extension}", FileFormatRegistry.VAG.file_filter,
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
                f"sample_{sample.spu_index}{FileFormatRegistry.WAV.extension}", FileFormatRegistry.WAV.file_filter,
            )

            if path:
                wav = self._window._vag_decoder.decode_to_wav(
                    sample.data, self._window._vag_rate.rate,
                )
                Path(path).write_bytes(wav)
                self._window.status.showMessage(f"Exported SPU {sample.spu_index} as WAV")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def add_sample(self, bank_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Add Sample to Bank", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )

        if not path:
            return

        try:
            vag = self._window._vag_reader.read_file(path)
            # add_sample appends a new SPU entry in place; keep a restore point so
            # declining the residency guard leaves no dangling entry behind.
            spu_before = list(self._window.hwl.spu_addrs)
            new_blob = self._window._bank_builder.add_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                vag.data, self._window._bank_reader,
            )

            if not self._bank_within_limit(bank_index, new_blob):
                self._window.hwl.spu_addrs[:] = spu_before
                return

            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Add Sample to Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob, snapshot_spu=True),
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
            self._window, "Replace Sample", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )
        if not path:
            return

        try:
            vag = self._window._vag_reader.read_file(path)

            if not self._confirm_size_change(bank_index, sample_index, len(vag.data)):
                return

            spu_index = self._find_spu_index(bank_index, sample_index)
            spu_before = list(self._window.hwl.spu_addrs)

            shared = self._resolve_shared_sample(bank_index, spu_index, len(vag.data))
            if shared is SharedChoice.CANCEL:
                return

            companions = self._companion_blobs(
                shared, spu_before, spu_index, vag.data, bank_index,
            )

            new_blob = self._window._bank_builder.replace_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, vag.data, self._window._bank_reader,
            )

            if not self._bank_within_limit(bank_index, new_blob):
                self._window.hwl.spu_addrs[:] = spu_before
                return

            self._push_replacement(bank_index, new_blob, companions)

            if spu_index is not None:
                self._propagate_sample_rate_to_fx(spu_index, vag.sample_rate)

            self._window._notify(self._replace_message(bank_index, sample_index, companions))
            self._warn_if_bank_oversized(bank_index, len(new_blob))
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Replace failed:\n{e}")

    def _resolve_shared_sample(
        self, bank_index: int, spu_index: int | None, new_data_len: int,
    ) -> 'SharedChoice':
        """Ask what to do when the sample's id is claimed by other banks too.

        Their blobs are cut using the size entry this edit would move, so
        leaving them untouched corrupts them silently — the user has to be told
        before the write, not after."""
        guard = self._window._shared_sample_guard

        if guard is None or spu_index is None:
            return SharedChoice.ALONE

        check = guard.check(self._window.hwl, bank_index, spu_index, new_data_len)
        if check.within_limit:
            return SharedChoice.ALONE

        return self._ask_shared_sample(check)

    def _ask_shared_sample(self, check) -> 'SharedChoice':
        box = QMessageBox(self._window)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Sample shared with other banks")
        box.setText(check.warning_text)
        update = box.addButton("Update all owning banks", QMessageBox.AcceptRole)
        only = box.addButton("Only this bank", QMessageBox.DestructiveRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(update)
        box.exec()

        clicked = box.clickedButton()
        if clicked is update:
            return SharedChoice.UPDATE_ALL
        if clicked is only:
            return SharedChoice.THIS_ONLY

        return SharedChoice.CANCEL

    def _companion_blobs(
        self,
        choice: 'SharedChoice',
        spu_before: list,
        spu_index: int | None,
        new_data: bytes,
        bank_index: int,
    ) -> dict[int, bytes]:
        """Rebuilt blobs for the co-owning banks, computed against the size
        table as it stands now — before `replace_sample` moves the entry."""
        propagator = self._window._shared_sample_propagator

        if choice is not SharedChoice.UPDATE_ALL or propagator is None or spu_index is None:
            return {}

        return propagator.rebuild_owners(
            self._window.hwl, spu_before, spu_index, new_data, bank_index,
        )

    def _push_replacement(
        self, bank_index: int, new_blob: bytes, companions: dict[int, bytes],
    ) -> None:
        """One undo step covers the edit and every bank dragged along with it,
        so undoing can't leave the file half-propagated."""
        stack = self._window._undo_stack

        if companions:
            stack.beginMacro(f"Replace Sample in Bank {bank_index} (+{len(companions)} shared)")

        stack.push(SwapBlobCommand(
            self._window, f"Replace Sample in Bank {bank_index}",
            HowlCollection.BANKS, bank_index, new_blob, snapshot_spu=True,
        ))

        for other_index, blob in companions.items():
            stack.push(SwapBlobCommand(
                self._window, f"Update Shared Sample in Bank {other_index}",
                HowlCollection.BANKS, other_index, blob, snapshot_spu=False,
            ))

        if companions:
            stack.endMacro()

    def _replace_message(
        self, bank_index: int, sample_index: int, companions: dict[int, bytes],
    ) -> str:
        base = f"Replaced sample {sample_index} in bank {bank_index}"

        if not companions:
            return base

        return f"{base} (also updated bank(s) {sorted(companions)})"

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

        pitch = int(round(sample_rate / spu.SAMPLE_RATE * spu.FREQUENCY_UNIT))
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
            f"⚠️ Bank {bank_index} is {bank_size} bytes — {over_by} over the "
            f"Saphi {SAPHI_BANK_MAX_SIZE}-byte limit. Saphi will reject the export.",
            10000,
        )

    def copy_sample(self, src_bank: int, src_sample: int) -> None:
        """Copy a sample's data into another bank — either appended as a new
        sample or replacing an existing slot in the target bank."""
        if not self._window.hwl:
            return

        try:
            src_samples = self._window._bank_reader.parse(
                self._window.hwl.banks[src_bank], self._window.hwl.spu_addrs,
            )

            if src_sample >= len(src_samples):
                return

            src = src_samples[src_sample]
            banks = self._build_copy_bank_summaries()
            size_text = self._window._size_formatter.format_bytes(len(src.data))
            source_display = self._bank_display(src_bank)
            summary = (
                f"Copy sample {src_sample} from {source_display} "
                f"(SPU #{src.spu_index}, {size_text}) to:"
            )
            dialog = CopyTargetDialog(
                self._window,
                title="Copy Sample",
                prompt=summary,
                container_label="Target bank:",
                child_label="Target sample:",
                append_label="(Append as new sample)",
                containers=banks,
                source_container_index=src_bank,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            target = dialog.chosen_target()
            if target is None:
                return

            self._apply_copy(src.data, target.container_index, target.child_index)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Copy failed:\n{e}")

    def _build_copy_bank_summaries(self) -> list[CopyTargetContainer]:
        out: list[CopyTargetContainer] = []

        for i, blob in enumerate(self._window.hwl.banks):
            try:
                samples = self._window._bank_reader.parse(blob, self._window.hwl.spu_addrs)
                child_labels = tuple(
                    f"Sample {slot} — SPU #{s.spu_index}"
                    for slot, s in enumerate(samples)
                )
            except Exception:
                child_labels = ()

            out.append(CopyTargetContainer(
                index=i, display=self._bank_display(i), child_labels=child_labels,
            ))

        return out

    def _bank_display(self, index: int) -> str:
        name = self._window._bank_reader.get_name(index)
        return f"Bank {index} — {name}" if name else f"Bank {index}"

    def _apply_copy(
        self, src_data: bytes, target_bank: int, target_sample: int | None,
    ) -> None:
        spu_before = list(self._window.hwl.spu_addrs)

        if target_sample is None:
            new_blob = self._window._bank_builder.add_sample(
                self._window.hwl.banks[target_bank], self._window.hwl.spu_addrs,
                src_data, self._window._bank_reader,
            )
            description = f"Copy sample into Bank {target_bank}"
            message = f"Copied sample as new entry in bank {target_bank}"
        else:
            if not self._confirm_size_change(target_bank, target_sample, len(src_data)):
                return

            new_blob = self._window._bank_builder.replace_sample(
                self._window.hwl.banks[target_bank], self._window.hwl.spu_addrs,
                target_sample, src_data, self._window._bank_reader,
            )
            description = f"Copy sample over Bank {target_bank} sample {target_sample}"
            message = f"Replaced sample {target_sample} in bank {target_bank}"

        if not self._bank_within_limit(target_bank, new_blob):
            self._window.hwl.spu_addrs[:] = spu_before
            return

        self._window._undo_stack.push(SwapBlobCommand(
            self._window, description, HowlCollection.BANKS, target_bank, new_blob,
            snapshot_spu=True,
        ))
        self._window._notify(message)
        self._warn_if_bank_oversized(target_bank, len(new_blob))

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
                SwapBlobCommand(self._window, f"Remove Sample {sample_index} from Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob, snapshot_spu=True),
            )
            self._window._notify(f"Removed sample {sample_index} from bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Remove failed:\n{e}")
