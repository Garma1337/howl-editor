# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr.formats.howl.blob_snapshot import BlobSnapshot
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr.formats.howl.versions import KNOWN_VERSIONS


@dataclass(frozen=True)
class HowlStats:
    """One snapshot of HowlFile-level numbers."""

    version_name: str
    bank_count: int
    modified_bank_count: int
    song_count: int
    modified_song_count: int
    other_fx_count: int
    engine_fx_count: int
    sample_bytes: int                   # total addressed sample data across all banks
    sample_entry_count: int             # number of SPU addr entries
    payload_bytes: int                  # sum of all bank + song blobs at present
    original_payload_bytes: int | None  # same sum from the load-time snapshot


class HowlStatsCalculator:
    """Builds a `HowlStats` from a HOWL file and an optional load-time snapshot."""

    def compute(self, hwl: HowlFile, snapshot: BlobSnapshot) -> HowlStats:
        return HowlStats(
            version_name=self._version_name(hwl),
            bank_count=len(hwl.banks),
            modified_bank_count=self._modified_count(hwl.banks, snapshot.banks),
            song_count=len(hwl.songs),
            modified_song_count=self._modified_count(hwl.songs, snapshot.songs),
            other_fx_count=len(hwl.other_fx),
            engine_fx_count=len(hwl.engine_fx),
            sample_bytes=sum(e.byte_size for e in hwl.spu_addrs),
            sample_entry_count=len(hwl.spu_addrs),
            payload_bytes=self._payload_bytes(hwl.banks, hwl.songs),
            original_payload_bytes=(
                self._payload_bytes(snapshot.banks, snapshot.songs)
                if snapshot.banks is not None and snapshot.songs is not None else None
            ),
        )

    def _version_name(self, hwl: HowlFile) -> str:
        return KNOWN_VERSIONS.get(hwl.version, f"Unknown (0x{hwl.version:02X})")

    def _modified_count(self, current: list[bytes], original: list[bytes] | None) -> int:
        if original is None:
            return 0

        return sum(
            1 for i, blob in enumerate(current)
            if i >= len(original) or blob != original[i]
        )

    def _payload_bytes(
        self, banks: list[bytes] | None, songs: list[bytes] | None,
    ) -> int:
        total = 0

        if banks is not None:
            total += sum(len(b) for b in banks)

        if songs is not None:
            total += sum(len(s) for s in songs)

        return total
