# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.diagnostics.howl_diagnostics import (
    Category, HowlDiagnostics, Severity, TargetKind,
)
from howl_editor.ctr.diagnostics.howl_size_guard import HowlSizeGuard
from howl_editor.ctr.diagnostics.pitch_ceiling_validator import PitchCeilingValidator
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1.formats.vag.structure_validator import VagStructureValidator
from howl_editor.ctr.formats.cseq.models import (
    CseqEvent, CseqEventType, CseqInstrument, CseqSong, CseqTrack,
)
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.ps1.constants import SECTOR_SIZE
from howl_editor.ps1.formats.vag import format as fmt
from tests.conftest import build_bank_blob, build_cseq_bytes


@pytest.fixture
def diagnostics(bank_reader, cseq_reader, validator, stock_layout):
    return HowlDiagnostics(
        cseq_reader, CseqSizeValidator(), bank_reader,
        SpuResidencyCalculator(bank_reader), validator, stock_layout,
        HowlSizeGuard(),
        BankSliceValidator(bank_reader, VagStructureValidator()),
        PitchCeilingValidator(PitchCalculator()),
    )


def _vag(byte_len: int) -> bytes:
    """A structurally sound one-shot VAG of `byte_len` bytes.

    Bank samples have to be real VAG or the slice check reports them, which
    would drown out whatever a test is actually asserting."""
    frames = byte_len // fmt.FRAME_SIZE
    body = b"".join(bytes([0x00, 0x00]) + b"\x00" * 14 for _ in range(frames - 1))

    return body + bytes([0x00, fmt.FLAG_LOOP_END]) + b"\x00" * 14


def _categories(report, severity=None):
    return {
        (f.category, f.target.kind, f.target.index)
        for f in report.findings
        if severity is None or f.severity is severity
    }


class TestHowlDiagnostics:

    def test_oversized_song_is_an_error(self, diagnostics):
        base = build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])
        blob = base + b"\x00" * (constants.MAX_CSEQ_BYTES + 2048 - len(base))
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.songs = [blob]

        report = diagnostics.diagnose(hwl, howl_file_size=len(blob), iso_budget_bytes=None)

        assert (Category.CSEQ_SIZE, TargetKind.SONG, 0) in _categories(report, Severity.ERROR)

    def test_out_of_range_sample_id_is_an_error(self, diagnostics):
        song = build_cseq_bytes(instruments=[CseqInstrument(sample_id=99)])
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)] * 5   # only ids 0..4 exist
        hwl.songs = [song]

        report = diagnostics.diagnose(hwl, howl_file_size=len(song), iso_budget_bytes=None)

        errors = _categories(report, Severity.ERROR)
        assert (Category.SAMPLE_REFERENCE, TargetKind.SONG, 0) in errors

    def test_level_residency_overflow_is_a_warning_on_the_bank(self, diagnostics):
        # Song 0 is Dingo Canyon -> paired bank 1. Make bank 1 huge.
        # Over-budget samples go silent (not a crash), so this is a warning.
        big_units = (constants.SPU_USABLE_SAMPLE_BYTES + 8192) // 8
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2), SpuAddrEntry(0, big_units)]
        hwl.banks = [
            build_bank_blob([0], [_vag(16)]),
            build_bank_blob([1], [_vag(big_units * 8)]),
        ]
        hwl.songs = [build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])]

        report = diagnostics.diagnose(hwl, howl_file_size=1024, iso_budget_bytes=None)

        warnings = _categories(report, Severity.WARNING)
        assert (Category.SPU_RESIDENCY, TargetKind.BANK, 1) in warnings
        assert (Category.SPU_RESIDENCY, TargetKind.BANK, 1) not in _categories(report, Severity.ERROR)

    def test_foreign_sample_is_a_warning(self, diagnostics):
        # Song 0 references id 3, which is in neither bank 0 nor its paired bank 1.
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)] * 4
        hwl.banks = [
            build_bank_blob([0], [_vag(16)]),
            build_bank_blob([1], [_vag(16)]),
        ]
        hwl.songs = [build_cseq_bytes(instruments=[CseqInstrument(sample_id=3)])]

        report = diagnostics.diagnose(hwl, howl_file_size=1024, iso_budget_bytes=None)

        warnings = _categories(report, Severity.WARNING)
        assert (Category.SAMPLE_REFERENCE, TargetKind.SONG, 0) in warnings

    def test_file_over_iso_budget_is_an_error(self, diagnostics):
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]

        report = diagnostics.diagnose(
            hwl, howl_file_size=3 * SECTOR_SIZE + 1, iso_budget_bytes=3 * SECTOR_SIZE,
        )

        assert (Category.HOWL_SIZE, TargetKind.FILE, None) in _categories(report, Severity.ERROR)

    def test_note_past_the_spu_pitch_ceiling_is_a_warning(self, diagnostics):
        """It plays flat rather than failing to load, so it warns."""
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=0, frequency=4096)],
            songs=[CseqSong(bpm=120, tpqn=480, tracks=[CseqTrack(flags=0, events=[
                CseqEvent(event_type=CseqEventType.CHANGE_PATCH, pitch=0),
                CseqEvent(event_type=CseqEventType.NOTE_ON, pitch=84, velocity=100),
                CseqEvent(event_type=CseqEventType.END_TRACK),
            ])])],
        )
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.songs = [song]

        report = diagnostics.diagnose(hwl, howl_file_size=len(song), iso_budget_bytes=None)

        assert (Category.PITCH_CEILING, TargetKind.SONG, 0) in _categories(report, Severity.WARNING)
        assert (Category.PITCH_CEILING, TargetKind.SONG, 0) not in _categories(report, Severity.ERROR)

    def test_mis_sliced_bank_is_an_error(self, diagnostics):
        """A bank whose blob no longer matches the size it is cut with — what a
        shared sample being resized elsewhere leaves behind."""
        hwl = HowlFile()
        # The bank carries one 16-byte sample, but the table says 32.
        hwl.spu_addrs = [SpuAddrEntry(0, 4)]
        hwl.banks = [build_bank_blob([0, 0], [_vag(16), _vag(16)])]

        report = diagnostics.diagnose(hwl, howl_file_size=2048, iso_budget_bytes=None)

        assert (Category.BANK_SLICING, TargetKind.BANK, 0) in _categories(report, Severity.ERROR)

    def test_clean_file_has_only_the_summary(self, diagnostics):
        hwl = HowlFile()
        hwl.spu_addrs = [SpuAddrEntry(0, 2)]
        hwl.banks = [build_bank_blob([0], [_vag(16)])]
        hwl.songs = [build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])]

        report = diagnostics.diagnose(hwl, howl_file_size=2048, iso_budget_bytes=None)

        assert report.counts()[Severity.ERROR] == 0
        assert report.counts()[Severity.WARNING] == 0
        assert report.counts()[Severity.INFO] == 1   # the summary
