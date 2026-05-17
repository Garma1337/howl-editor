# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from howl_editor.cseq.adventure_hub import ADVENTURE_HUB_NUM_SEQUENCES
from howl_editor.gui.command import SwapBlobCommand
from howl_editor.gui.dialog.convert_midi_dialog import ConvertMidiDialog
from howl_editor.gui.entry_drop_router import DropAction, EntryDropRouter
from howl_editor.midi.converter import HAS_MIDO
from howl_editor.models import EntryLeaf, EntryRow, LeafKind
from howl_editor.models.semantic_entry import EntryKind


class EntryRowHandler:
    """Bridge between Main-tab entry rows / leaves and the existing handlers."""

    def __init__(self, window, drop_router: EntryDropRouter):
        self._w = window
        self._router = drop_router

    def play(self, row: EntryRow) -> None:
        if not self._w.hwl:
            return

        playback = self._w._playback
        if row.kind == EntryKind.OTHER_FX and row.fx_index is not None:
            playback.play_other_fx(row.fx_index)
        elif row.kind == EntryKind.ENGINE_FX and row.fx_index is not None:
            playback.play_engine_fx(row.fx_index)

    def export(self, row: EntryRow) -> None:
        if not self._w.hwl:
            return

        if row.song_index is not None:
            self._w._song_handler.export_song(row.song_index)
            return

        if row.bank_index is not None:
            self._w._bank_handler.export_bank(row.bank_index)

    def replace(self, row: EntryRow) -> None:
        if not self._w.hwl or not row.accepts:
            return

        ext_filter = " ".join(f"*{e}" for e in row.accepts)
        path, _ = QFileDialog.getOpenFileName(
            self._w, f"Replace {row.name}", "",
            f"Accepted files ({ext_filter});;All Files (*)",
        )

        if not path:
            return

        self._dispatch_drop(row, path)

    def on_drop(self, row: EntryRow, file_path: str) -> None:
        self._dispatch_drop(row, file_path)

    def reset(self, row: EntryRow) -> None:
        snapshot = self._w._snapshot

        if row.song_index is not None:
            original = snapshot.original_song(row.song_index)

            if original is not None:
                self._w._undo_stack.push(SwapBlobCommand(
                    self._w, f"Reset song {row.song_index}", "songs",
                    row.song_index, original,
                ))
                self._w._notify(f"Reset {row.name} to stock")

        if row.bank_index is not None:
            original = snapshot.original_bank(row.bank_index)

            if original is not None:
                self._w._undo_stack.push(SwapBlobCommand(
                    self._w, f"Reset bank {row.bank_index}", "banks",
                    row.bank_index, original,
                ))
                self._w._notify(f"Reset {row.name} to stock")

    def play_leaf(self, leaf: EntryLeaf) -> None:
        if not self._w.hwl:
            return

        if leaf.kind == LeafKind.SEQUENCE and leaf.song_index is not None:
            self._w._playback.play_sequence(leaf.song_index, leaf.seq_index or 0)
            return

        if leaf.kind == LeafKind.SAMPLE and leaf.bank_index is not None:
            self._w._playback.play_sample(leaf.bank_index, leaf.sample_index or 0)

    def replace_leaf(self, leaf: EntryLeaf) -> None:
        if leaf.kind == LeafKind.SEQUENCE and leaf.song_index is not None:
            self._w._song_handler.replace_sequence(leaf.song_index, leaf.seq_index or 0)
            return

        if leaf.kind == LeafKind.SAMPLE and leaf.bank_index is not None:
            self._w._sample_handler.replace_sample(leaf.bank_index, leaf.sample_index or 0)

    def export_leaf(self, leaf: EntryLeaf) -> None:
        if leaf.kind == LeafKind.SEQUENCE and leaf.song_index is not None:
            self._w._song_handler.export_sequence_as_midi(
                leaf.song_index, leaf.seq_index or 0,
            )
            return

        if leaf.kind == LeafKind.SAMPLE and leaf.bank_index is not None:
            # Default to WAV — friendlier for music makers; VAG is in File Content.
            self._w._sample_handler.export_sample_as_wav(
                leaf.bank_index, leaf.sample_index or 0,
            )

    def play_hub_preview(self, song_index: int, seq_indices: list[int], label: str) -> None:
        """Render the layered hub preview for the selected hub and play it."""
        if not self._w.hwl:
            return

        self._w._playback.play_layered(song_index, list(seq_indices), label)

    def drop_leaf(self, leaf: EntryLeaf, file_path: str) -> None:
        # Direct file → leaf replacement, skipping the file picker that
        # replace_leaf normally opens.
        if leaf.kind == LeafKind.SEQUENCE and leaf.song_index is not None:
            self._w._song_handler.replace_sequence(leaf.song_index, leaf.seq_index or 0)
            return

        if leaf.kind == LeafKind.SAMPLE and leaf.bank_index is not None:
            self._w._sample_handler.replace_sample(leaf.bank_index, leaf.sample_index or 0)

    def _dispatch_drop(self, row: EntryRow, file_path: str) -> None:
        route = self._router.resolve(row, file_path)
        if route is None:
            self._w.status.showMessage(
                f"Cannot use {Path(file_path).name} for {row.name}",
            )

            return

        try:
            if route.action == DropAction.REPLACE_SONG:
                self._replace_song_with_cseq(row, file_path)
            elif route.action == DropAction.REPLACE_BANK:
                self._replace_bank_with_bnk(row, file_path)
            elif route.action == DropAction.CONVERT_MIDI_TO_SONG:
                self._replace_song_with_midi(row, file_path)
            elif route.action == DropAction.IMPORT_SCA_INTO_TRACK:
                self._replace_track_with_sca(row, file_path)
            elif route.action == DropAction.REPLACE_FX_SAMPLE:
                self._notify_unsupported("FX sample replacement: open the File Content tab")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Replace failed:\n{e}")

    def _replace_song_with_cseq(self, row: EntryRow, file_path: str) -> None:
        if row.song_index is None:
            return

        blob = Path(file_path).read_bytes()

        if row.kind == EntryKind.ADVENTURE_HUB and not self._validate_hub_cseq(blob, file_path):
            return

        self._w._undo_stack.push(SwapBlobCommand(
            self._w, f"Replace song {row.song_index}", "songs",
            row.song_index, blob,
        ))
        self._w._notify(f"Replaced {row.name} with {Path(file_path).name}")

    def _validate_hub_cseq(self, blob: bytes, file_path: str) -> bool:
        try:
            cseq = self._w._cseq_reader.read(blob)
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Cannot read CSEQ:\n{e}")
            return False

        if len(cseq.songs) != ADVENTURE_HUB_NUM_SEQUENCES:
            QMessageBox.warning(
                self._w, "Adventure Hub CSEQ rejected",
                f"{Path(file_path).name} has {len(cseq.songs)} sequences. "
                f"The Adventure Hub layered song requires exactly "
                f"{ADVENTURE_HUB_NUM_SEQUENCES}; replacing with a different "
                f"count breaks the per-hub mask layering at runtime.",
            )
            return False

        return True

    def _replace_bank_with_bnk(self, row: EntryRow, file_path: str) -> None:
        if row.bank_index is None:
            return

        blob = Path(file_path).read_bytes()
        self._w._undo_stack.push(SwapBlobCommand(
            self._w, f"Replace bank {row.bank_index}", "banks",
            row.bank_index, blob,
        ))
        self._w._notify(f"Replaced {row.name} with {Path(file_path).name}")

    def _replace_song_with_midi(self, row: EntryRow, file_path: str) -> None:
        if row.song_index is None or not HAS_MIDO:
            self._notify_unsupported("MIDI support requires the 'mido' package")
            return

        try:
            info = self._w._midi_converter.get_midi_info(file_path)
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Cannot read MIDI:\n{e}")
            return

        max_spu = len(self._w.hwl.spu_addrs) if self._w.hwl else 0
        dialog = ConvertMidiDialog(self._w, info, max_spu)

        if dialog.exec() != QDialog.Accepted:
            return

        try:
            cseq_blob = self._w._midi_converter.convert(file_path, dialog.get_settings())
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Conversion failed:\n{e}")
            return

        self._w._undo_stack.push(SwapBlobCommand(
            self._w, f"Replace song {row.song_index} from MIDI", "songs",
            row.song_index, cseq_blob,
        ))
        self._w._notify(f"Replaced {row.name} with {Path(file_path).name}")

    def _replace_track_with_sca(self, row: EntryRow, file_path: str) -> None:
        if row.song_index is None or row.bank_index is None:
            self._notify_unsupported("SCA drop needs a row with both song and bank slots")
            return

        try:
            sca = self._w._sca_reader.parse(Path(file_path).read_bytes())
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Failed to parse .sca file:\n{e}")
            return

        self._w._undo_stack.push(SwapBlobCommand(
            self._w, f"Replace bank {row.bank_index} from SCA", "banks",
            row.bank_index, sca.bank,
        ))
        self._w._undo_stack.push(SwapBlobCommand(
            self._w, f"Replace song {row.song_index} from SCA", "songs",
            row.song_index, sca.cseq,
        ))
        self._w._notify(
            f"Replaced {row.name} with \"{sca.metadata.name}\" by {sca.metadata.author}",
        )

    def _notify_unsupported(self, message: str) -> None:
        self._w.status.showMessage(message)
