# coding: utf-8

from howl_editor.ctr.analysis.howl_stats import HowlStatsCalculator
from howl_editor.ctr.formats.howl.blob_snapshot import BlobSnapshot
from howl_editor.ctr.formats.howl.models import (
    HowlFile, SpuAddrEntry, OtherFX, EngineFX, HowlHeader,
)
from howl_editor.ctr.formats.howl.versions import KNOWN_VERSIONS


def _hwl(
    banks=(b"\x00" * 16, b"\x00" * 32),
    songs=(b"\x00" * 8,),
    spu_sizes=(2, 4, 6),
    other_fx_count=1,
    engine_fx_count=2,
    version=HowlHeader.VERSION_RELEASE,
) -> HowlFile:
    return HowlFile(
        version=version,
        spu_addrs=[SpuAddrEntry(0, s) for s in spu_sizes],
        other_fx=[OtherFX()] * other_fx_count,
        engine_fx=[EngineFX()] * engine_fx_count,
        banks=list(banks),
        songs=list(songs),
    )


class TestHowlStatsCalculator:

    def test_basic_counts(self):
        stats = HowlStatsCalculator().compute(_hwl(), BlobSnapshot())

        assert stats.bank_count == 2
        assert stats.song_count == 1
        assert stats.other_fx_count == 1
        assert stats.engine_fx_count == 2

    def test_sample_bytes_sums_spu_sizes_in_bytes(self):
        # SpuAddrEntry stores size in 8-byte units; byte_size multiplies by 8.
        stats = HowlStatsCalculator().compute(
            _hwl(spu_sizes=(2, 4, 6)), BlobSnapshot(),
        )

        assert stats.sample_bytes == (2 + 4 + 6) * 8
        assert stats.sample_entry_count == 3

    def test_payload_bytes_sums_bank_and_song_blob_lengths(self):
        stats = HowlStatsCalculator().compute(
            _hwl(banks=(b"\x00" * 100, b"\x00" * 200), songs=(b"\x00" * 50,)),
            BlobSnapshot(),
        )

        assert stats.payload_bytes == 100 + 200 + 50

    def test_release_version_name(self):
        stats = HowlStatsCalculator().compute(_hwl(), BlobSnapshot())
        assert stats.version_name == KNOWN_VERSIONS[HowlHeader.VERSION_RELEASE]

    def test_unknown_version_name_includes_hex(self):
        stats = HowlStatsCalculator().compute(_hwl(version=0xAB), BlobSnapshot())
        assert "0xAB" in stats.version_name

    def test_modified_counts_zero_without_snapshot(self):
        stats = HowlStatsCalculator().compute(_hwl(), BlobSnapshot())

        assert stats.modified_bank_count == 0
        assert stats.modified_song_count == 0

    def test_modified_bank_count_with_snapshot(self):
        hwl = _hwl(banks=(b"\x11" * 16, b"\x22" * 16), songs=(b"\x00" * 8,))
        snapshot = BlobSnapshot()
        snapshot.capture(hwl)

        # Mutate one bank — modified count should rise to 1.
        hwl.banks[1] = b"\x33" * 16
        stats = HowlStatsCalculator().compute(hwl, snapshot)

        assert stats.modified_bank_count == 1
        assert stats.modified_song_count == 0

    def test_original_payload_bytes_present_when_snapshot_captured(self):
        hwl = _hwl()
        snapshot = BlobSnapshot()
        snapshot.capture(hwl)

        stats = HowlStatsCalculator().compute(hwl, snapshot)
        expected = sum(len(b) for b in hwl.banks) + sum(len(s) for s in hwl.songs)
        assert stats.original_payload_bytes == expected

    def test_original_payload_bytes_none_without_snapshot(self):
        stats = HowlStatsCalculator().compute(_hwl(), BlobSnapshot())
        assert stats.original_payload_bytes is None
