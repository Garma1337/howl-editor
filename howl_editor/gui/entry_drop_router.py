# coding: utf-8

from dataclasses import dataclass
from pathlib import Path

from howl_editor.gui.entries.semantic_entry import EntryKind
from howl_editor.gui.entries.semantic_entry import EntryRow


class DropAction:
    REPLACE_SONG = "replace_song"
    REPLACE_BANK = "replace_bank"
    CONVERT_MIDI_TO_SONG = "convert_midi_to_song"
    IMPORT_SCA_INTO_TRACK = "import_sca_into_track"
    REPLACE_FX_SAMPLE = "replace_fx_sample"


@dataclass
class DropRoute:
    action: str
    file_path: str
    row: EntryRow


class EntryDropRouter:
    """Resolves the action to perform when a file is dropped on an entry row."""

    def resolve(self, row: EntryRow, file_path: str) -> DropRoute | None:
        ext = Path(file_path).suffix.lower()

        if ext not in row.accepts:
            return None

        action = self._action_for(row.kind, ext)
        if action is None:
            return None

        return DropRoute(action=action, file_path=file_path, row=row)

    def _action_for(self, kind: EntryKind, ext: str) -> str | None:
        # Track or shared song: route by source file type.
        if kind in (EntryKind.TRACK, EntryKind.SHARED_SONG, EntryKind.CUSTOM_SONG):
            if ext == ".cseq":
                return DropAction.REPLACE_SONG

            if ext == ".mid":
                return DropAction.CONVERT_MIDI_TO_SONG

            if ext == ".sca":
                return DropAction.IMPORT_SCA_INTO_TRACK

            return None

        # Adventure Hub: same as track but no .sca path (mask layering would break).
        if kind == EntryKind.ADVENTURE_HUB:
            if ext == ".cseq":
                return DropAction.REPLACE_SONG

            if ext == ".mid":
                return DropAction.CONVERT_MIDI_TO_SONG

            return None

        # Bank-only entries (characters, boss banks, SFX universal, custom banks).
        if kind in (EntryKind.BANK_ONLY, EntryKind.CUSTOM_BANK):
            if ext == ".bnk":
                return DropAction.REPLACE_BANK

            return None

        # FX entries take a raw sample.
        if kind in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX):
            if ext in (".vag", ".wav"):
                return DropAction.REPLACE_FX_SAMPLE

            return None

        return None
