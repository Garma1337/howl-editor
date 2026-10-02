# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from howl_editor.ctr import constants
from howl_editor.ctr.formats.bank.models import BankSample
from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.command import SwapBlobCommand
from howl_editor.gui.dialog.copy_target_dialog import (
    CopyTargetContainer, CopyTargetDialog,
)
from howl_editor.gui.dialog.replace_sample_dialog import ReplaceSampleDialog
from howl_editor.gui.dialog.select_sample_dialog import SelectSampleDialog
from howl_editor.ps1 import spu
from howl_editor.ps1.formats.vag.models import VagSample
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE


class SampleHandler:

    def __init__(self, window):
        self._window = window

    def _bank_within_limit(self, index: int, blob) -> bool:
        """See BankHandler._bank_within_limit."""
        guard = self._window._services.resolve("bank_size_guard")
        return guard is None or self._window.confirm_within_limit(
            guard.check(self._window.hwl, index, blob),
        )

    def export_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._services.resolve("bank_reader").parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export Sample SPU {sample.spu_index}",
                f"sample_{sample.spu_index}{FileFormatRegistry.VAG.extension}", FileFormatRegistry.VAG.file_filter,
            )

            if path:
                self._window._services.resolve("vag_writer").write_file(VagSample(data=sample.data), path)
                self._window._notify(f"Exported SPU {sample.spu_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def export_sample_as_wav(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._services.resolve("bank_reader").parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export WAV SPU {sample.spu_index}",
                f"sample_{sample.spu_index}{FileFormatRegistry.WAV.extension}", FileFormatRegistry.WAV.file_filter,
            )

            if path:
                wav = self._window._services.resolve("vag_decoder").decode_to_wav(
                    sample.data, self._window._services.resolve("vag_rate_provider").rate,
                )
                Path(path).write_bytes(wav)
                self._window._notify(f"Exported SPU {sample.spu_index} as WAV")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def add_sample(self, bank_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Add Sample to Bank", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )

        if path:
            self.add_sample_from_file(bank_index, path)

    def add_sample_from_file(self, bank_index: int, path: str):
        """Add a VAG to a bank in the SPU slot the user picks."""
        if not self._window.hwl:
            return

        try:
            vag = self._window._services.resolve("vag_reader").read_file(path)
            spu_index = self._pick_new_slot(f"Add {Path(path).name} to {self._bank_display(bank_index)}")

            if spu_index is None:
                return

            # add_sample writes the SPU entry in place; keep a restore point so
            # declining the residency guard leaves no dangling entry behind.
            spu_before = list(self._window.hwl.spu_addrs)
            new_blob = self._window._services.resolve("bank_builder").add_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                vag.data, self._window._services.resolve("bank_reader"), spu_index=spu_index,
            )

            if not self._bank_within_limit(bank_index, new_blob):
                self._window.hwl.spu_addrs[:] = spu_before
                return

            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Add Sample to Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob, old_spu=spu_before),
            )

            self._window._services.resolve("howl_editor").attach_sample_rate(self._window.hwl, spu_index, vag.sample_rate)
            self._window._notify(f"Added sample SPU {spu_index} to bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Add sample failed:\n{e}")

    def _pick_new_slot(self, subject: str, share_spu: int | None = None) -> int | None:
        """Ask which SPU slot a new sample goes into. None when cancelled."""
        choices = self._window._services.resolve("spu_slot_choices")
        hwl = self._window.hwl
        default = choices.default_new_slot(hwl, share_spu)

        if default is None:
            QMessageBox.warning(
                self._window, "No free SPU slot",
                f"All {constants.MAX_SPU_SLOTS} SPU slots are in use, so the new sample has "
                f"nowhere to go. Remove a sample from every bank that holds it to free its "
                f"slot, or replace an existing sample instead.",
            )
            return None

        dialog = SelectSampleDialog(
            self._window,
            title="Pick SPU slot",
            prompt=(
                f"{subject}\n\nPick the SPU slot for the new sample. Slots marked "
                f"🆓 free are unused; greyed-out slots already belong to something else."
            ),
            choices=choices.new_sample_slots(hwl, share_spu),
            current_spu_index=default,
        )

        if dialog.exec() != QDialog.Accepted:
            return None

        return dialog.chosen_spu_index()

    def replace_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Replace Sample", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )
        if not path:
            return

        try:
            vag = self._window._services.resolve("vag_reader").read_file(path)
            plan = self._window._services.resolve("sample_replacement_planner").plan(
                self._window.hwl, bank_index, sample_index, vag.data,
            )

            update_shared = self._confirm_replacement(plan, Path(path).name, bank_index)

            if update_shared is None:
                return

            self._apply_replacement(
                plan, vag.data, update_shared, sample_rate=vag.sample_rate,
            )
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Replace failed:\n{e}")

    def _confirm_replacement(self, plan, source_label: str, bank_index: int) -> bool | None:
        """Show the one prompt that covers a sample overwrite. None = cancelled,
        otherwise whether the banks sharing the slot should be rebuilt too."""
        dialog = ReplaceSampleDialog(
            self._window, plan, source_label, self._bank_display(bank_index),
        )

        if dialog.exec() != QDialog.Accepted:
            return None

        return dialog.chosen().update_shared_banks

    def _apply_replacement(
        self, plan, new_data: bytes, update_shared: bool,
        sample_rate: int | None = None, verb: str = "Replaced",
    ) -> None:
        """Write the planned replacement. The plan was built against copies, so
        the companion blobs are rebuilt here against the live table — before
        replace_sample moves the size entry."""
        spu_before = list(self._window.hwl.spu_addrs)
        companions = (
            self._window._services.resolve("shared_sample_propagator").rebuild_owners(
                self._window.hwl, spu_before, plan.spu_index, new_data, plan.bank_index,
            )
            if update_shared and plan.spu_index is not None else {}
        )

        new_blob = self._window._services.resolve("bank_builder").replace_sample(
            self._window.hwl.banks[plan.bank_index], self._window.hwl.spu_addrs,
            plan.sample_index, new_data, self._window._services.resolve("bank_reader"),
        )

        self._push_replacement(plan.bank_index, new_blob, companions, spu_before)

        if sample_rate is not None and plan.spu_index is not None:
            self._propagate_sample_rate_to_fx(plan.spu_index, sample_rate)

        self._window._notify(
            self._replace_message(plan.bank_index, plan.sample_index, companions, verb),
        )
        self._warn_if_bank_oversized(plan.bank_index, len(new_blob))

    def _push_replacement(
        self, bank_index: int, new_blob: bytes, companions: dict[int, bytes],
        spu_before: list,
    ) -> None:
        """One undo step covers the edit and every bank dragged along with it,
        so undoing can't leave the file half-propagated."""
        stack = self._window._undo_stack

        if companions:
            stack.beginMacro(f"Replace Sample in Bank {bank_index} (+{len(companions)} shared)")

        stack.push(SwapBlobCommand(
            self._window, f"Replace Sample in Bank {bank_index}",
            HowlCollection.BANKS, bank_index, new_blob, old_spu=spu_before,
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
        verb: str = "Replaced",
    ) -> str:
        base = f"{verb} sample {sample_index} in bank {bank_index}"

        if not companions:
            return base

        return f"{base} (also updated bank(s) {sorted(companions)})"

    def _find_spu_index(self, bank_index: int, sample_index: int) -> int | None:
        try:
            samples = self._window._services.resolve("bank_reader").parse(
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

    def _warn_if_bank_oversized(self, bank_index: int, bank_size: int) -> None:
        if bank_size <= SAPHI_BANK_MAX_SIZE:
            return

        over_by = bank_size - SAPHI_BANK_MAX_SIZE
        self._window._notify(
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
            src_samples = self._window._services.resolve("bank_reader").parse(
                self._window.hwl.banks[src_bank], self._window.hwl.spu_addrs,
            )

            if src_sample >= len(src_samples):
                return

            src = src_samples[src_sample]
            banks = self._build_copy_bank_summaries()
            size_text = self._window._services.resolve("size_formatter").format_bytes(len(src.data))
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

            self._apply_copy(src, target.container_index, target.child_index)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Copy failed:\n{e}")

    def _build_copy_bank_summaries(self) -> list[CopyTargetContainer]:
        out: list[CopyTargetContainer] = []

        for i, blob in enumerate(self._window.hwl.banks):
            try:
                samples = self._window._services.resolve("bank_reader").parse(blob, self._window.hwl.spu_addrs)
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
        name = self._window._services.resolve("bank_reader").get_name(index)
        return f"Bank {index} — {name}" if name else f"Bank {index}"

    def _apply_copy(
        self, src: BankSample, target_bank: int, target_sample: int | None,
    ) -> None:
        if target_sample is not None:
            self._copy_over_sample(src, target_bank, target_sample)
            return

        target_blob = self._window.hwl.banks[target_bank]
        # Identical audio can share the source's slot — unless the target
        # bank already holds that slot, where sharing would list it twice.
        already_there = src.spu_index in self._window._services.resolve("bank_reader").sample_ids(target_blob)
        spu_index = self._pick_new_slot(
            f"Copy SPU #{src.spu_index} into {self._bank_display(target_bank)}",
            share_spu=None if already_there else src.spu_index,
        )

        if spu_index is None:
            return

        spu_before = list(self._window.hwl.spu_addrs)
        new_blob = self._window._services.resolve("bank_builder").add_sample(
            target_blob, self._window.hwl.spu_addrs,
            src.data, self._window._services.resolve("bank_reader"), spu_index=spu_index,
        )

        if not self._bank_within_limit(target_bank, new_blob):
            self._window.hwl.spu_addrs[:] = spu_before
            return

        self._window._undo_stack.push(SwapBlobCommand(
            self._window, f"Copy sample into Bank {target_bank}",
            HowlCollection.BANKS, target_bank, new_blob, old_spu=spu_before,
        ))
        self._window._notify(
            f"Copied sample into bank {target_bank} as SPU #{spu_index}",
        )
        self._warn_if_bank_oversized(target_bank, len(new_blob))

    def _copy_over_sample(self, src: BankSample, target_bank: int, target_sample: int) -> None:
        """Copying onto an existing sample overwrites a slot exactly as a file
        replacement does, so it takes the same plan and prompt."""
        plan = self._window._services.resolve("sample_replacement_planner").plan(
            self._window.hwl, target_bank, target_sample, src.data,
        )
        update_shared = self._confirm_replacement(
            plan, f"SPU #{src.spu_index}", target_bank,
        )

        if update_shared is None:
            return

        self._apply_replacement(plan, src.data, update_shared, verb="Copied over")

    def remove_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        if QMessageBox.question(
            self._window, "Remove Sample", f"Remove sample {sample_index} from bank {bank_index}?",
        ) != QMessageBox.Yes:
            return

        try:
            new_blob = self._window._services.resolve("bank_builder").remove_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, self._window._services.resolve("bank_reader"),
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Remove Sample {sample_index} from Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob, snapshot_spu=True),
            )
            self._window._notify(f"Removed sample {sample_index} from bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Remove failed:\n{e}")
