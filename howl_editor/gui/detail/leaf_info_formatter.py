# coding: utf-8

from howl_editor.audio.sample_lookup import SampleLookup
from howl_editor.bank.reader import BankReader
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.cseq.reader import CseqReader
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.models import EntryLeaf, HowlFile, LeafKind
from howl_editor.models.semantic_entry import EntryKind, EntryRow


# Sony ADPCM (VAG) format: 16-byte blocks decode to 28 mono int16 samples.
_VAG_BLOCK_BYTES = 16
_VAG_BLOCK_SAMPLES = 28


class LeafInfoFormatter:
    """Renders the Main-tab side-panel HTML for a selection — either a single
    leaf (sample / sequence) or the entry header (bank / song / FX)."""

    def __init__(
        self,
        template_engine: TemplateEngine,
        bank_reader: BankReader,
        cseq_reader: CseqReader,
        sample_lookup: SampleLookup,
        size_formatter: SizeFormatter,
    ):
        self._engine = template_engine
        self._bank = bank_reader
        self._cseq = cseq_reader
        self._lookup = sample_lookup
        self._sizes = size_formatter

    def format(self, leaf: EntryLeaf, hwl: HowlFile | None = None) -> str:
        rows = self._rows_for_leaf(leaf, hwl)
        return self._render(leaf.name, rows)

    def format_entry(
        self, row: EntryRow, hwl: HowlFile | None = None,
        leaves: list[EntryLeaf] | None = None,
    ) -> str:
        rows = self._rows_for_entry(row, hwl, leaves)
        return self._render(row.name, rows)

    def _render(self, title: str, rows: list[dict]) -> str:
        body = self._engine.render("key_value.html", title=title, rows=rows)
        return self._engine.render("document.html", body=body)

    def _rows_for_leaf(self, leaf: EntryLeaf, hwl: HowlFile | None) -> list[dict]:
        if leaf.kind == LeafKind.SEQUENCE:
            return self._sequence_rows(leaf, hwl)

        if leaf.kind == LeafKind.SAMPLE:
            return self._sample_rows(leaf, hwl)

        return []

    def _sequence_rows(self, leaf: EntryLeaf, hwl: HowlFile | None) -> list[dict]:
        rows: list[dict] = [{"key": "Type", "value": "Sequence"}]

        if leaf.song_index is not None:
            rows.append({"key": "Song slot", "value": str(leaf.song_index)})

        if leaf.seq_index is not None:
            rows.append({"key": "Sub-song", "value": str(leaf.seq_index)})

        if hwl is None or leaf.song_index is None or leaf.seq_index is None:
            return rows

        if leaf.song_index >= len(hwl.songs):
            return rows

        try:
            cseq = self._cseq.read(hwl.songs[leaf.song_index])
        except Exception:
            return rows

        if leaf.seq_index < len(cseq.songs):
            sub_song = cseq.songs[leaf.seq_index]
            rows.append({"key": "Tempo", "value": f"{sub_song.bpm} BPM"})
            rows.append({"key": "TPQN", "value": str(sub_song.tpqn)})
            rows.append({"key": "Tracks", "value": str(len(sub_song.tracks))})

            event_total = sum(len(t.events) for t in sub_song.tracks)
            rows.append({"key": "Events", "value": str(event_total)})

        return rows

    def _sample_rows(self, leaf: EntryLeaf, hwl: HowlFile | None) -> list[dict]:
        rows: list[dict] = [{"key": "Type", "value": "Sample"}]

        if leaf.bank_index is not None:
            rows.append({"key": "Bank slot", "value": str(leaf.bank_index)})

        if leaf.sample_index is not None:
            rows.append({"key": "Sample index", "value": str(leaf.sample_index)})

        if leaf.spu_index is not None:
            rows.append({"key": "SPU index", "value": str(leaf.spu_index)})

        if (
            hwl is None or leaf.bank_index is None or leaf.sample_index is None
            or leaf.bank_index >= len(hwl.banks)
        ):
            return rows

        try:
            samples = self._bank.parse(hwl.banks[leaf.bank_index], hwl.spu_addrs)
        except Exception:
            return rows

        if leaf.sample_index >= len(samples):
            return rows

        sample = samples[leaf.sample_index]
        sample_bytes = len(sample.data)
        rows.append({"key": "Size", "value": self._sizes.format_bytes(sample_bytes)})

        try:
            sample_rate = self._lookup.lookup_sample_rate(hwl, sample.spu_index)
        except Exception:
            sample_rate = None

        if sample_rate:
            rows.append({"key": "Sample rate", "value": f"{sample_rate} Hz"})
            duration = self._estimate_duration_seconds(sample_bytes, sample_rate)
            if duration > 0:
                rows.append({"key": "Length", "value": self._format_duration(duration)})

        return rows

    def _rows_for_entry(
        self, row: EntryRow, hwl: HowlFile | None,
        leaves: list[EntryLeaf] | None,
    ) -> list[dict]:
        rows: list[dict] = []

        kind_label = self._entry_kind_label(row.kind)
        if kind_label:
            rows.append({"key": "Type", "value": kind_label})

        rows.extend(self._leaf_breakdown_rows(leaves))

        if row.is_modified:
            rows.append({"key": "Status", "value": "Modified (unsaved)"})

        if row.is_broken:
            rows.append({"key": "Status", "value": f"Broken — missing {row.missing_count} sample(s)"})

        if row.song_index is not None:
            rows.append({"key": "Song slot", "value": str(row.song_index)})

            if hwl is not None and row.song_index < len(hwl.songs):
                rows.extend(self._song_summary_rows(hwl.songs[row.song_index]))

        if row.bank_index is not None:
            rows.append({"key": "Bank slot", "value": str(row.bank_index)})

            if hwl is not None and row.bank_index < len(hwl.banks):
                rows.extend(self._bank_summary_rows(hwl.banks[row.bank_index]))

        if row.fx_index is not None:
            rows.append({"key": "FX index", "value": str(row.fx_index)})
            rows.extend(self._fx_summary_rows(row, hwl))

        return rows

    def _fx_summary_rows(self, row: EntryRow, hwl: HowlFile | None) -> list[dict]:
        """Pull the SPU index / volume / pitch off the matching FX entry so
        the sidebar shows useful metadata when an FX row is clicked — the row
        is otherwise just a name and the abstract `fx_index`."""
        if hwl is None or row.fx_index is None:
            return []

        if row.kind == EntryKind.OTHER_FX:
            table = hwl.other_fx
        elif row.kind == EntryKind.ENGINE_FX:
            table = hwl.engine_fx
        else:
            return []

        if row.fx_index >= len(table):
            return []

        fx = table[row.fx_index]
        rows: list[dict] = [
            {"key": "SPU index", "value": str(fx.spu_index)},
            {"key": "Volume", "value": str(fx.volume)},
            {"key": "Pitch", "value": str(fx.pitch)},
        ]

        if row.kind == EntryKind.OTHER_FX:
            rows.append({"key": "Duration", "value": str(fx.duration)})

        return rows

    def _leaf_breakdown_rows(self, leaves: list[EntryLeaf] | None) -> list[dict]:
        """Break the leaf list into a total count plus a kind breakdown.
        Replaces the inline `61 items` chip that used to live in the entry
        header — surfacing the same number plus what's underneath it."""
        if not leaves:
            return []

        sample_count = sum(1 for leaf in leaves if leaf.kind == LeafKind.SAMPLE)
        sequence_count = sum(1 for leaf in leaves if leaf.kind == LeafKind.SEQUENCE)
        total = len(leaves)

        rows: list[dict] = [{"key": "Items", "value": str(total)}]

        if sample_count:
            rows.append({"key": "Samples", "value": str(sample_count)})

        if sequence_count:
            rows.append({"key": "Sequences", "value": str(sequence_count)})

        return rows

    def _entry_kind_label(self, kind: EntryKind) -> str:
        return {
            EntryKind.TRACK: "Track (song + bank)",
            EntryKind.SHARED_SONG: "Shared song",
            EntryKind.BANK_ONLY: "Bank",
            EntryKind.ADVENTURE_HUB: "Adventure Hub",
            EntryKind.OTHER_FX: "Sound effect",
            EntryKind.ENGINE_FX: "Engine sound",
            EntryKind.CUSTOM_SONG: "Custom song",
            EntryKind.CUSTOM_BANK: "Custom bank",
        }.get(kind, "")

    def _song_summary_rows(self, song_blob: bytes) -> list[dict]:
        rows: list[dict] = [{"key": "Song size", "value": self._sizes.format_bytes(len(song_blob))}]

        try:
            info = self._cseq.get_info(song_blob)
        except Exception:
            return rows

        rows.append({"key": "Instruments", "value": str(info.num_instruments)})
        rows.append({"key": "Percussions", "value": str(info.num_percussions)})
        rows.append({"key": "Sub-songs", "value": str(info.num_songs)})
        return rows

    def _bank_summary_rows(self, bank_blob: bytes) -> list[dict]:
        rows: list[dict] = [{"key": "Bank size", "value": self._sizes.format_bytes(len(bank_blob))}]

        try:
            samples = self._bank.parse(bank_blob, [])
        except Exception:
            # Bank parse needs SPU addrs to compute sample sizes; if we don't
            # have them, just report the sample count from the header.
            samples = []

        if samples:
            rows.append({"key": "Samples", "value": str(len(samples))})

        return rows

    def _estimate_duration_seconds(self, vag_bytes: int, sample_rate: int) -> float:
        """Rough duration for a VAG-encoded sample. 16 source bytes decode to
        28 mono int16 samples — accurate enough for an info-panel readout."""
        if vag_bytes <= 0 or sample_rate <= 0:
            return 0.0

        pcm_samples = (vag_bytes // _VAG_BLOCK_BYTES) * _VAG_BLOCK_SAMPLES
        return pcm_samples / sample_rate

    def _format_duration(self, seconds: float) -> str:
        if seconds < 1.0:
            return f"{seconds * 1000:.0f} ms"

        if seconds < 60.0:
            return f"{seconds:.2f} s"

        minutes = int(seconds // 60)
        rest = seconds - minutes * 60
        return f"{minutes}:{rest:05.2f}"
