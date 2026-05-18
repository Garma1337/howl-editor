# coding: utf-8

from howl_editor.analysis.blob_modification_detector import BlobModificationDetector
from howl_editor.analysis.stock_layout import StockLayout
from howl_editor.bank.reader import BankReader
from howl_editor.cseq.adventure_hub import (
    ADVENTURE_HUB_BANK_INDEX, ADVENTURE_HUB_SONG_INDEX, AdventureHubMaskTable,
)
from howl_editor.cseq.reader import CseqReader
from howl_editor.models import HowlFile
from howl_editor.models.semantic_entry import EntryGroup, EntryKind, EntryRow


class SemanticEntryBuilder:
    """Builds the grouped EntryRow list shown on the Main tab from a HowlFile."""

    def __init__(
        self,
        bank_reader: BankReader,
        cseq_reader: CseqReader,
        stock_layout: StockLayout,
        modification_detector: BlobModificationDetector,
        hub_mask_table: AdventureHubMaskTable
    ):
        self._bank = bank_reader
        self._cseq = cseq_reader
        self._layout = stock_layout
        self._mod = modification_detector
        self._hub_mask = hub_mask_table

    def build(
        self,
        hwl: HowlFile,
        original_banks: list[bytes] | None = None,
        original_songs: list[bytes] | None = None,
    ) -> list[EntryGroup]:
        modified_banks = self._mod.modified_indices(hwl.banks, original_banks)
        modified_songs = self._mod.modified_indices(hwl.songs, original_songs)
        n_banks = len(hwl.banks)
        n_songs = len(hwl.songs)

        groups = [
            self._track_group(
                "Race Tracks", "🏁", self._layout.RACE_TRACK_SONG_RANGE,
                n_banks, n_songs, modified_banks, modified_songs,
            ),
            self._track_group(
                "Battle Arenas", "⚔️", self._layout.BATTLE_ARENA_SONG_RANGE,
                n_banks, n_songs, modified_banks, modified_songs,
            ),
            self._adventure_hub_group(hwl, modified_banks, modified_songs),
            self._boss_group(n_banks, n_songs, modified_banks, modified_songs),
            self._track_group(
                "Menus & Cinematics", "🎬", self._layout.MENU_SONG_RANGE,
                n_banks, n_songs, modified_banks, modified_songs,
            ),
            self._character_group(n_banks, modified_banks),
            self._sfx_universal_group(n_banks, modified_banks),
            self._other_fx_group(hwl),
            self._engine_fx_group(hwl),
            self._custom_group(n_banks, n_songs, modified_banks, modified_songs),
        ]

        return [g for g in groups if g.rows]

    def _track_group(self, name, icon, song_range, n_banks, n_songs,
                     modified_banks, modified_songs) -> EntryGroup:
        group = EntryGroup(name=name, icon=icon)

        for song_idx in song_range:
            if song_idx >= n_songs:
                continue

            bank_idx = self._layout.paired_bank(song_idx)
            if bank_idx is not None and bank_idx >= n_banks:
                bank_idx = None

            label = self._cseq.get_name(song_idx) or f"Song {song_idx}"
            is_mod = (
                song_idx in modified_songs
                or (bank_idx is not None and bank_idx in modified_banks)
            )

            group.rows.append(EntryRow(
                kind=EntryKind.TRACK,
                name=label,
                song_index=song_idx,
                bank_index=bank_idx,
                is_modified=is_mod,
                accepts=(".mid", ".cseq", ".sca"),
            ))

        return group

    def _adventure_hub_group(self, hwl, modified_banks, modified_songs) -> EntryGroup:
        """Adventure Hub music is one CSEQ (#26) and one shared bank (#31)."""
        group = EntryGroup(name="Adventure Hub", icon="🌍")
        song_idx = ADVENTURE_HUB_SONG_INDEX
        bank_idx = ADVENTURE_HUB_BANK_INDEX

        song_present = song_idx < len(hwl.songs)
        bank_present = bank_idx < len(hwl.banks)

        if not song_present and not bank_present:
            return group

        group.rows.append(EntryRow(
            kind=EntryKind.ADVENTURE_HUB,
            name="Adventure Hub",
            song_index=song_idx if song_present else None,
            bank_index=bank_idx if bank_present else None,
            is_modified=(
                (song_present and song_idx in modified_songs)
                or (bank_present and bank_idx in modified_banks)
            ),
            accepts=(".mid", ".cseq"),
        ))

        return group

    def _boss_group(self, n_banks, n_songs, modified_banks, modified_songs) -> EntryGroup:
        group = EntryGroup(name="Boss Themes", icon="👹")
        boss_song_idx = self._layout.BOSS_SONG_INDEX

        if boss_song_idx < n_songs:
            group.rows.append(EntryRow(
                kind=EntryKind.SHARED_SONG,
                name=self._cseq.get_name(boss_song_idx) or "Boss Race",
                song_index=boss_song_idx,
                is_modified=boss_song_idx in modified_songs,
                accepts=(".mid", ".cseq"),
            ))

        for bank_idx in self._layout.BOSS_BANK_RANGE:
            if bank_idx >= n_banks:
                continue

            group.rows.append(EntryRow(
                kind=EntryKind.BANK_ONLY,
                name=self._bank.get_name(bank_idx) or f"Bank {bank_idx}",
                bank_index=bank_idx,
                is_modified=bank_idx in modified_banks,
                accepts=(".bnk",),
            ))

        return group

    def _character_group(self, n_banks, modified_banks) -> EntryGroup:
        group = EntryGroup(name="Characters", icon="🏎️", collapsed_by_default=True)

        for bank_idx in self._layout.CHARACTER_BANK_RANGE:
            if bank_idx >= n_banks:
                continue

            group.rows.append(EntryRow(
                kind=EntryKind.BANK_ONLY,
                name=self._bank.get_name(bank_idx) or f"Bank {bank_idx}",
                bank_index=bank_idx,
                is_modified=bank_idx in modified_banks,
                accepts=(".bnk",),
            ))

            podium_idx = self._layout.podium_bank_for_character(bank_idx)
            if podium_idx is None or podium_idx >= n_banks:
                continue

            group.rows.append(EntryRow(
                kind=EntryKind.BANK_ONLY,
                name=self._bank.get_name(podium_idx) or f"Bank {podium_idx}",
                bank_index=podium_idx,
                is_modified=podium_idx in modified_banks,
                accepts=(".bnk",),
            ))

        return group

    def _sfx_universal_group(self, n_banks, modified_banks) -> EntryGroup:
        group = EntryGroup(name="SFX (universal)", icon="📦", collapsed_by_default=True)
        bank_idx = self._layout.SFX_UNIVERSAL_BANK

        if bank_idx < n_banks:
            group.rows.append(EntryRow(
                kind=EntryKind.BANK_ONLY,
                name=self._bank.get_name(bank_idx) or "SFX (universal)",
                bank_index=bank_idx,
                is_modified=bank_idx in modified_banks,
                accepts=(".bnk",),
            ))

        return group

    def _other_fx_group(self, hwl) -> EntryGroup:
        group = EntryGroup(name="Sound Effects (OtherFX)", icon="🔊", collapsed_by_default=True)

        for i, _ in enumerate(hwl.other_fx):
            group.rows.append(EntryRow(
                kind=EntryKind.OTHER_FX,
                name=f"FX #{i}",
                fx_index=i,
                accepts=(".vag", ".wav"),
            ))

        return group

    def _engine_fx_group(self, hwl) -> EntryGroup:
        group = EntryGroup(name="Engine Sounds (EngineFX)", icon="🚗", collapsed_by_default=True)

        for i, _ in enumerate(hwl.engine_fx):
            group.rows.append(EntryRow(
                kind=EntryKind.ENGINE_FX,
                name=f"Engine #{i}",
                fx_index=i,
                accepts=(".vag", ".wav"),
            ))

        return group

    def _custom_group(self, n_banks, n_songs, modified_banks, modified_songs) -> EntryGroup:
        group = EntryGroup(name="Custom", icon="✨")

        for song_idx in range(self._layout.FIRST_CUSTOM_SONG, n_songs):
            group.rows.append(EntryRow(
                kind=EntryKind.CUSTOM_SONG,
                name=f"Custom song #{song_idx}",
                song_index=song_idx,
                is_modified=song_idx in modified_songs,
                accepts=(".mid", ".cseq", ".sca"),
            ))

        for bank_idx in range(self._layout.FIRST_CUSTOM_BANK, n_banks):
            group.rows.append(EntryRow(
                kind=EntryKind.CUSTOM_BANK,
                name=f"Custom bank #{bank_idx}",
                bank_index=bank_idx,
                is_modified=bank_idx in modified_banks,
                accepts=(".bnk",),
            ))

        return group
