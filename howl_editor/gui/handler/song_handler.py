# coding: utf-8

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QInputDialog

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.ps1 import spu
from howl_editor.gui.command import RemoveItemCommand, SwapBlobCommand
from howl_editor.gui.dialog.copy_target_dialog import (
    CopyTargetContainer, CopyTargetDialog,
)
from howl_editor.gui.dialog.edit_instrument_dialog import EditInstrumentDialog
from howl_editor.gui.dialog.midi_export_options_dialog import MidiExportOptionsDialog
from howl_editor.gui.dialog.convert_midi_dialog import ConvertMidiDialog
from howl_editor.gui.dialog.select_sample_dialog import (
    SampleChoice, SelectSampleDialog,
)
from howl_editor.midi.converter import HAS_MIDO
from howl_editor.midi.exporter import MidiExportOptions


class SongHandler:

    def __init__(self, window):
        self._w = window

    def _cseq_within_limit(self, blob) -> bool:
        """Gate a prospective CSEQ blob through the engine size guard, warning
        (with override) if it exceeds the console's song buffer."""
        guard = self._w._cseq_size_guard
        return guard is None or self._w.confirm_within_limit(guard.check(blob))

    def add_song(self):
        if not self._w.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self._w, "Add Song", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)")
        if not path:
            return

        data = Path(path).read_bytes()
        if not self._cseq_within_limit(data):
            return

        self._w._editor.add_song(self._w.hwl, data)
        self._w._mark_modified()
        self._w._rebuild_tree()
        self._w._notify(f"Added song {len(self._w.hwl.songs) - 1} from {Path(path).name}")

    def export_song(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self._w, f"Export Song {index}", f"song_{index}{FileFormatRegistry.CSEQ.extension}", FileFormatRegistry.CSEQ.file_filter)

        if path:
            Path(path).write_bytes(self._w.hwl.songs[index])
            self._w.status.showMessage(f"Exported song {index}")

    def _prompt_midi_options(self) -> MidiExportOptions | None:
        """Cache the last-used options on the handler so a user who exports
        many sequences in a row doesn't have to re-check the boxes each time."""
        defaults = getattr(self, "_last_midi_options", MidiExportOptions())
        dialog = MidiExportOptionsDialog(self._w, defaults)

        if dialog.exec() != QDialog.Accepted:
            return None

        options = dialog.chosen()
        self._last_midi_options = options
        return options

    def export_song_as_midi(self, index: int):
        if not self._w.hwl or not self._w._midi_exporter:
            return

        options = self._prompt_midi_options()
        if options is None:
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

                self._w._midi_exporter.export_to_file(cseq, out, i, options)

            self._w.status.showMessage(f"Exported song {index} as MIDI")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"MIDI export failed:\n{e}")

    def export_sequence_as_midi(self, song_index: int, seq_index: int):
        if not self._w.hwl or not self._w._midi_exporter:
            return

        options = self._prompt_midi_options()
        if options is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self._w, f"Export Sequence {seq_index}",
            f"song_{song_index}_seq{seq_index}{FileFormatRegistry.MIDI.extension}", FileFormatRegistry.MIDI.file_filter,
        )
        if not path:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            self._w._midi_exporter.export_to_file(cseq, path, seq_index, options)
            self._w.status.showMessage(f"Exported sequence {seq_index} as MIDI")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"MIDI export failed:\n{e}")

    def export_song_as_sfz(self, index: int):
        """Write a song as an SFZ patch (text manifest + samples folder).
        Lets a music maker load the song's sound palette into any
        SFZ-compatible DAW / sampler instead of treating the data as opaque
        CSEQ bytes."""
        if not self._w.hwl or self._w._sfz_exporter is None:
            return

        song_name = self._w._cseq_reader.get_name(index) or f"song_{index}"
        default_name = f"{self._w._sfz_exporter.safe_filename_stem(song_name)}{FileFormatRegistry.SFZ.extension}"

        path, _ = QFileDialog.getSaveFileName(
            self._w, f"Export Song {index} as SFZ",
            default_name, FileFormatRegistry.SFZ.file_filter,
        )

        if not path:
            return

        try:
            written = self._w._sfz_exporter.export(
                self._w.hwl, index, Path(path), self._w._vag_rate.rate,
            )
            self._w.status.showMessage(
                f"Exported song {index} as SFZ ({written} samples)",
            )
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"SFZ export failed:\n{e}")

    def replace_song(self, index: int):
        path, _ = QFileDialog.getOpenFileName(self._w, f"Replace Song {index}", "", f"{FileFormatRegistry.CSEQ.file_filter};;All Files (*)")
        if not path:
            return

        data = Path(path).read_bytes()
        if not self._cseq_within_limit(data):
            return

        self._w._undo_stack.push(
            SwapBlobCommand(self._w, f"Replace Song {index}", HowlCollection.SONGS, index, data),
        )
        self._w._notify(f"Replaced song {index} with {Path(path).name}")

    def remove_song(self, index: int):
        if QMessageBox.question(self._w, "Remove Song", f"Remove song {index}?") == QMessageBox.Yes:
            self._w._undo_stack.push(
                RemoveItemCommand(self._w, f"Remove Song {index}", HowlCollection.SONGS, index),
            )
            self._w._notify(f"Removed song {index}")

    def replace_sequence(self, song_index: int, seq_index: int):
        """Replace a single sequence from a picked file. Accepts a CSEQ (pick
        which sub-song to graft in) or a MIDI (opens the convert dialog). Only
        the target sequence is swapped — the song's other sequences, e.g. the
        Aku Aku / Uka Uka masks on songs 0-27, are left intact."""
        if not self._w.hwl:
            return

        both = FileFormatRegistry.create_combined_filter(
            "Sequence Files", FileFormatRegistry.CSEQ, FileFormatRegistry.MIDI,
        )
        path, _ = QFileDialog.getOpenFileName(
            self._w, "Select Source Sequence", "",
            f"{both};;{FileFormatRegistry.CSEQ.file_filter};;{FileFormatRegistry.MIDI.file_filter};;All Files (*)",
        )
        if not path:
            return

        self.replace_sequence_from_file(song_index, seq_index, path)

    def replace_sequence_from_file(self, song_index: int, seq_index: int, path: str):
        """Apply a specific source file to one sequence, skipping the picker.
        Used by both the menu (via replace_sequence) and drag-and-drop."""
        if not self._w.hwl:
            return

        try:
            source_seq = self._resolve_source_sequence(path, song_index)
            if source_seq is None:
                return

            new_blob = self._w._cseq_editor.replace_sequence(
                self._w.hwl.songs[song_index], seq_index, source_seq,
            )
            if not self._cseq_within_limit(new_blob):
                return

            self._w._undo_stack.push(
                SwapBlobCommand(self._w, f"Replace Sequence in Song {song_index}", HowlCollection.SONGS, song_index, new_blob),
            )
            self._w._notify(f"Replaced sequence {seq_index} in song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Replace failed:\n{e}")

    def _resolve_source_sequence(self, path: str, song_index: int):
        """Turn a picked/dropped file into the single CseqSong to graft into
        the target sequence. Returns None if the user cancels a sub-dialog."""
        if Path(path).suffix.lower() in FileFormatRegistry.MIDI.extensions:
            cseq = self._import_midi_as_cseq(path, self._paired_bank(song_index))
            if cseq is None or not cseq.songs:
                return None

            return cseq.songs[0]

        source_cseq = self._w._cseq_reader.read(Path(path).read_bytes())
        if not source_cseq.songs:
            raise ValueError("Source CSEQ has no sequences")

        source_seq_index = 0
        if len(source_cseq.songs) > 1:
            labels = [f"Sequence {i} (BPM={s.bpm}, {len(s.tracks)} tracks)"
                      for i, s in enumerate(source_cseq.songs)]
            label, ok = QInputDialog.getItem(
                self._w, "Select Sequence", "Pick sequence from source:", labels, 0, False,
            )

            if not ok:
                return None

            source_seq_index = labels.index(label)

        return source_cseq.songs[source_seq_index]

    def _paired_bank(self, song_index: int) -> int | None:
        if self._w._stock_layout is None:
            return None

        return self._w._stock_layout.paired_bank(song_index)

    def import_midi_as_cseq(self, path: str, bank_index: int | None):
        """Public entry for MIDI → whole-CSEQ import. Returns the converted
        CseqFile model, or None if MIDI support is missing or the user cancels
        the mapping dialog."""
        return self._import_midi_as_cseq(path, bank_index)

    def _import_midi_as_cseq(self, path: str, bank_index: int | None):
        if not HAS_MIDO or self._w._midi_converter is None:
            self._w.status.showMessage("MIDI support requires the 'mido' package")
            return None

        try:
            info = self._w._midi_converter.get_midi_info(path)
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Cannot read MIDI:\n{e}")
            return None

        max_spu = len(self._w.hwl.spu_addrs) if self._w.hwl else 0
        bank_order = None
        spu_rates = None
        if self._w._sample_lookup is not None and self._w.hwl is not None:
            # Rates for every referenced sample — so both the initial prefill and
            # any later SPU change in the dialog resolve a frequency, not just
            # the paired bank's samples.
            spu_rates = self._w._sample_lookup.sample_rate_map(self._w.hwl) or None
            if bank_index is not None:
                bank_order = self._w._sample_lookup.bank_spu_order(self._w.hwl, bank_index) or None

        dialog = ConvertMidiDialog(
            self._w, info, max_spu, self._w._drum_names, bank_order, spu_rates,
        )
        if dialog.exec() != QDialog.Accepted:
            return None

        try:
            return self._w._midi_converter.convert_to_model(path, dialog.get_settings())
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Conversion failed:\n{e}")
            return None

    def edit_instrument(self, song_index: int, inst_index: int):
        """Open a small dialog to tweak volume / pitch on one CSEQ
        instrument, then commit through an undoable SwapBlobCommand."""
        if not self._w.hwl:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            if inst_index >= len(cseq.instruments):
                return

            inst = cseq.instruments[inst_index]
            dialog = EditInstrumentDialog(
                self._w,
                title="Edit Instrument",
                subject_label=f"Editing instrument {inst_index} (SPU #{inst.sample_id})",
                initial_volume=inst.volume,
                initial_frequency=inst.frequency,
                initial_adsr=inst.adsr,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            result = dialog.chosen()
            new_blob = self._w._cseq_editor.update_instrument(
                self._w.hwl.songs[song_index], inst_index,
                result.volume, result.frequency, result.adsr,
            )

            self._w._undo_stack.push(SwapBlobCommand(
                self._w, f"Edit instrument {inst_index} in Song {song_index}",
                HowlCollection.SONGS, song_index, new_blob,
            ))

            self._w._notify(f"Updated instrument {inst_index} in song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Edit failed:\n{e}")

    def edit_percussion(self, song_index: int, perc_index: int):
        if not self._w.hwl:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            if perc_index >= len(cseq.percussions):
                return

            perc = cseq.percussions[perc_index]
            dialog = EditInstrumentDialog(
                self._w,
                title="Edit Percussion",
                subject_label=f"Editing percussion {perc_index} (SPU #{perc.sample_id})",
                initial_volume=perc.volume,
                initial_frequency=perc.frequency,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            result = dialog.chosen()
            new_blob = self._w._cseq_editor.update_percussion(
                self._w.hwl.songs[song_index], perc_index,
                result.volume, result.frequency,
            )
            self._w._undo_stack.push(SwapBlobCommand(
                self._w, f"Edit percussion {perc_index} in Song {song_index}",
                HowlCollection.SONGS, song_index, new_blob,
            ))
            self._w._notify(f"Updated percussion {perc_index} in song {song_index}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Edit failed:\n{e}")

    def replace_track_from_midi(self, song_index: int, seq_index: int, track_index: int):
        """Pick a MIDI file (and a track inside it if there are multiple),
        convert just that track's messages, and swap them into the named
        CSEQ track. Track flags / instrument binding stay put."""
        if not self._w.hwl or not self._w._midi_converter:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._w, "Select MIDI file", "",
            f"{FileFormatRegistry.MIDI.file_filter};;All Files (*)",
        )

        if not path:
            return

        try:
            info = self._w._midi_converter.get_midi_info(path)
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Cannot read MIDI:\n{e}")
            return

        # Filter to tracks that actually contain notes — empty meta-only
        # tracks (tempo track, lyrics, etc.) aren't useful targets.
        note_tracks = [t for t in info.tracks if t.note_count > 0]

        if not note_tracks:
            QMessageBox.warning(self._w, "No note tracks", "The MIDI file has no tracks with notes.")
            return

        midi_track_index = note_tracks[0].index

        if len(note_tracks) > 1:
            labels = [f"Track {t.index} — {t.name} ({t.note_count} notes)" for t in note_tracks]
            label, ok = QInputDialog.getItem(
                self._w, "Pick MIDI track",
                "Which MIDI track should replace the CSEQ track's events?",
                labels, 0, False,
            )

            if not ok:
                return

            midi_track_index = note_tracks[labels.index(label)].index

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            if seq_index >= len(cseq.songs) or track_index >= len(cseq.songs[seq_index].tracks):
                return

            instrument_index = cseq.songs[seq_index].tracks[track_index].instrument
            new_events = self._w._midi_converter.extract_track_events(
                path, midi_track_index, instrument_index,
            )

            new_blob = self._w._cseq_editor.replace_track_events(
                self._w.hwl.songs[song_index], seq_index, track_index, new_events,
            )
            self._w._undo_stack.push(SwapBlobCommand(
                self._w, f"Replace events on track {track_index}",
                HowlCollection.SONGS, song_index, new_blob,
            ))
            self._w._notify(
                f"Replaced track {track_index} (song {song_index} seq {seq_index}) "
                f"from {Path(path).name}",
            )
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Track import failed:\n{e}")

    def retarget_instrument(self, song_index: int, inst_index: int):
        """Point an instrument at a different SPU index in the same file."""
        self._retarget(song_index, inst_index, percussion=False)

    def retarget_percussion(self, song_index: int, perc_index: int):
        """Same as retarget_instrument but for the percussion table."""
        self._retarget(song_index, perc_index, percussion=True)

    def _retarget(self, song_index: int, entry_index: int, percussion: bool):
        if not self._w.hwl:
            return

        try:
            cseq = self._w._cseq_reader.read(self._w.hwl.songs[song_index])
            table = cseq.percussions if percussion else cseq.instruments

            if entry_index >= len(table):
                return

            current_id = table[entry_index].sample_id
            choices = self._build_sample_choices()
            kind = "percussion" if percussion else "instrument"
            dialog = SelectSampleDialog(
                self._w,
                title=f"Pick sample for {kind}",
                prompt=f"Select which SPU sample {kind} {entry_index} should point at:",
                choices=choices,
                current_spu_index=current_id,
                on_preview=self._preview_sample,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            new_id = dialog.chosen_spu_index()
            if new_id is None or new_id == current_id:
                return

            song_blob = self._w.hwl.songs[song_index]

            if percussion:
                new_blob = self._w._cseq_editor.retarget_percussion(song_blob, entry_index, new_id)
                description = f"Retarget percussion {entry_index} → SPU #{new_id}"
            else:
                new_blob = self._w._cseq_editor.retarget_instrument(song_blob, entry_index, new_id)
                description = f"Retarget instrument {entry_index} → SPU #{new_id}"

            self._w._undo_stack.push(SwapBlobCommand(
                self._w, description, HowlCollection.SONGS, song_index, new_blob,
            ))
            self._w._notify(f"{kind.capitalize()} {entry_index} now points at SPU #{new_id}")
        except Exception as e:
            QMessageBox.critical(self._w, "Error", f"Retarget failed:\n{e}")

    def _preview_sample(self, spu_index: int) -> None:
        """Audition a candidate sample straight from the retarget picker, at
        the rate the file already associates with it, so the user can hear it
        before committing the repoint."""
        if not self._w.hwl:
            return

        rate_hz = self._w._sample_lookup.lookup_sample_rate(self._w.hwl, spu_index)
        pitch = int(rate_hz * spu.FREQUENCY_UNIT / spu.SAMPLE_RATE)
        self._w._playback.play_spu_sample(spu_index, pitch, "Preview")

    def _build_sample_choices(self) -> list[SampleChoice]:
        """One option per entry in the SPU address table. Each choice is
        annotated with the source bank (if locatable) and byte size, so the
        user can tell what sample they're picking even without per-sample
        names."""
        out: list[SampleChoice] = []
        lookup = self._w._sample_lookup

        for spu_index in range(len(self._w.hwl.spu_addrs)):
            location = lookup.find_bank_and_sample_index(self._w.hwl, spu_index)
            size = self._w.hwl.spu_addrs[spu_index].byte_size

            if location is None:
                bank_label = "—"
            else:
                bank_index, _ = location
                name = self._w._bank_reader.get_name(bank_index)
                bank_label = (
                    f"Bank {bank_index} — {name}" if name else f"Bank {bank_index}"
                )

            display = f"SPU #{spu_index:>4} · {size:>6} B · {bank_label}"
            out.append(SampleChoice(spu_index=spu_index, display=display))

        return out

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
            if not self._cseq_within_limit(new_blob):
                return

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

        if not self._cseq_within_limit(new_blob):
            return

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
