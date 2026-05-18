# coding: utf-8

from howl_editor.ctr import track_masks
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.track_mask_layout import TrackMaskLayout
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.gui.entries.entry_leaf import EntryLeaf, LeafKind
from howl_editor.gui.entries.semantic_entry import EntryKind
from howl_editor.gui.entries.semantic_entry import EntryRow

_SAMPLE_ICON = "🔊"


class EntryLeavesBuilder:
    """Builds the per-leaf list for a single Main-tab entry."""

    def __init__(
        self,
        bank_reader: BankReader,
        cseq_reader: CseqReader,
        track_mask_layout: TrackMaskLayout,
    ):
        self._bank = bank_reader
        self._cseq = cseq_reader
        self._track_mask = track_mask_layout

    def build(self, hwl: HowlFile, row: EntryRow) -> list[EntryLeaf]:
        if row.kind in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX):
            return []  # FX entries ARE leaves themselves; no sub-leaves.

        leaves: list[EntryLeaf] = []

        if row.song_index is not None and row.song_index < len(hwl.songs):
            leaves.extend(self._song_leaves(hwl, row.song_index))

        if row.bank_index is not None and row.bank_index < len(hwl.banks):
            leaves.extend(self._bank_leaves(hwl, row.bank_index))

        return leaves

    def _song_leaves(self, hwl: HowlFile, song_index: int) -> list[EntryLeaf]:
        try:
            cseq = self._cseq.read(hwl.songs[song_index])
        except Exception:
            return []

        leaves: list[EntryLeaf] = []
        applies = self._track_mask.applies_to(song_index)

        for seq_idx in range(len(cseq.songs)):
            if applies and seq_idx < track_masks.NUM_MASK_SLOTS:
                name = self._track_mask.name_for(seq_idx)
                icon = self._track_mask.icon_for(seq_idx)
            else:
                name = f"Sequence {seq_idx}"
                icon = track_masks.GENERIC_SEQUENCE_ICON

            leaves.append(EntryLeaf(
                kind=LeafKind.SEQUENCE,
                name=name,
                icon=icon,
                song_index=song_index,
                seq_index=seq_idx,
            ))

        return leaves

    def _bank_leaves(self, hwl: HowlFile, bank_index: int) -> list[EntryLeaf]:
        try:
            samples = self._bank.parse(hwl.banks[bank_index], hwl.spu_addrs)
        except Exception:
            return []

        return [
            EntryLeaf(
                kind=LeafKind.SAMPLE,
                name=f"Sample {i}",
                icon=_SAMPLE_ICON,
                bank_index=bank_index,
                sample_index=i,
                spu_index=sample.spu_index,
            )
            for i, sample in enumerate(samples)
        ]
