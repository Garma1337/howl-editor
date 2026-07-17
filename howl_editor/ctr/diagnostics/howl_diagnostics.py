# coding: utf-8

from dataclasses import dataclass, field
from enum import Enum

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.diagnostics.howl_size_guard import HowlSizeGuard
from howl_editor.ctr.diagnostics.pitch_ceiling_validator import PitchCeilingValidator
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.analysis.stock_layout_resolver import StockLayoutResolver
from howl_editor.ctr.analysis.validator import BankCseqValidator
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr import stock_layout as layout
from howl_editor.ps1 import spu


class Severity(Enum):
    ERROR = 3
    WARNING = 2
    INFO = 1


class TargetKind(Enum):
    FILE = "file"
    BANK = "bank"
    SONG = "song"


class Category(Enum):
    """The kind of problem a finding reports. The value doubles as the label
    shown in the report list."""
    CSEQ_SIZE = "CSEQ size"
    UNREADABLE_SONG = "Unreadable song"
    SAMPLE_REFERENCE = "Sample reference"
    PITCH_CEILING = "Pitch ceiling"
    UNREADABLE_BANK = "Unreadable bank"
    BANK_SLICING = "Bank slicing"
    SPU_RESIDENCY = "SPU residency"
    HOWL_SIZE = "HOWL size"
    SUMMARY = "Summary"


@dataclass(frozen=True)
class Target:
    kind: TargetKind
    index: int | None = None


@dataclass(frozen=True)
class Finding:
    severity: Severity
    category: Category
    target: Target
    message: str


@dataclass(frozen=True)
class DiagnosisReport:
    findings: list[Finding] = field(default_factory=list)

    def counts(self) -> dict[Severity, int]:
        out = {Severity.ERROR: 0, Severity.WARNING: 0, Severity.INFO: 0}
        for f in self.findings:
            out[f.severity] += 1

        return out


class HowlDiagnostics:
    """Sweeps a whole HOWL file for data the console can't load: songs past the
    CSEQ buffer, banks that overflow SPU RAM for a race, broken sample
    references, un-parseable blobs, and a file grown past its ISO slot.

    Every finding carries a `Target` (file / bank / song) so the GUI can badge
    the offending item; the same report also drives the on-demand text report.
    """

    def __init__(
        self,
        cseq_reader: CseqReader,
        cseq_size_validator: CseqSizeValidator,
        bank_reader: BankReader,
        residency: SpuResidencyCalculator,
        validator: BankCseqValidator,
        stock_layout: StockLayoutResolver,
        howl_size_guard: HowlSizeGuard,
        slice_validator: BankSliceValidator,
        pitch_ceiling_validator: PitchCeilingValidator,
    ):
        self._cseq_reader = cseq_reader
        self._cseq_size = cseq_size_validator
        self._bank_reader = bank_reader
        self._residency = residency
        self._slices = slice_validator
        self._validator = validator
        self._layout = stock_layout
        self._howl_size = howl_size_guard
        self._pitch_ceiling = pitch_ceiling_validator

    def diagnose(
        self,
        hwl: HowlFile,
        *,
        howl_file_size: int,
        iso_budget_bytes: int | None,
    ) -> DiagnosisReport:
        findings: list[Finding] = []

        findings.extend(self._check_songs(hwl))
        findings.extend(self._check_bank_parsing(hwl))
        findings.extend(self._check_bank_slicing(hwl))
        findings.extend(self._check_level_residency(hwl))
        findings.extend(self._check_file_size(hwl, howl_file_size, iso_budget_bytes))
        findings.append(self._summary(hwl, howl_file_size))

        findings.sort(key=lambda f: -f.severity.value)
        return DiagnosisReport(findings=findings)

    def _check_songs(self, hwl: HowlFile) -> list[Finding]:
        out: list[Finding] = []

        for i, blob in enumerate(hwl.songs):
            name = self._song_label(i)

            if not self._cseq_size.is_within_limit(blob):
                over = self._cseq_size.calculate_overflow_bytes(blob)
                out.append(Finding(
                    Severity.ERROR, Category.CSEQ_SIZE, Target(TargetKind.SONG, i),
                    f"{name} is {len(blob)} bytes — {over} over the "
                    f"{constants.MAX_CSEQ_BYTES}-byte (0x5800) song buffer. The game "
                    f"overruns its buffer loading it, causing crashes or broken audio.",
                ))

            try:
                cseq = self._cseq_reader.read(blob)
            except Exception as e:
                out.append(Finding(
                    Severity.ERROR, Category.UNREADABLE_SONG, Target(TargetKind.SONG, i),
                    f"{name} could not be parsed as a CSEQ: {e}",
                ))
                continue

            out.extend(self._check_sample_refs(hwl, i, cseq, name))
            out.extend(self._check_pitch_ceiling(i, cseq, name))

        return out

    def _check_pitch_ceiling(self, song_index, cseq, name) -> list[Finding]:
        """Notes whose pitch register saturates the SPU. They play flat rather
        than failing, so this warns instead of erroring."""
        result = self._pitch_ceiling.validate(cseq)
        out: list[Finding] = []

        for item in result.exceedances:
            out.append(Finding(
                Severity.WARNING, Category.PITCH_CEILING, Target(TargetKind.SONG, song_index),
                f"{name}: {self._pitch_subject(item)} needs pitch {item.register} "
                f"({item.over_by} over the SPU's {spu.MAX_PITCH} ceiling). The console "
                f"cannot play faster than 4.0×, so this and every higher note collapse "
                f"onto the same pitch and the part goes flat. Lower the base pitch "
                f"(currently {item.base_pitch}) and speed the sample up to compensate.",
            ))

        return out

    def _pitch_subject(self, item) -> str:
        if item.is_drum:
            return f"percussion {item.slot} (SPU {item.sample_id})"

        return f"instrument {item.slot} (SPU {item.sample_id}) at note {item.note}"

    def _check_sample_refs(self, hwl, song_index, cseq, name) -> list[Finding]:
        out: list[Finding] = []
        required = self._validator.get_required_ids(cseq)
        n_spu = len(hwl.spu_addrs)

        out_of_range = sorted(sid for sid in required if sid < 0 or sid >= n_spu)
        if out_of_range:
            out.append(Finding(
                Severity.ERROR, Category.SAMPLE_REFERENCE, Target(TargetKind.SONG, song_index),
                f"{name} references sample id(s) {out_of_range} that don't exist in "
                f"this file ({n_spu} samples). The game reads past the sample table.",
            ))

        paired = self._layout.paired_bank(song_index)
        if paired is not None and 0 <= paired < len(hwl.banks) and hwl.banks:
            available = (
                self._validator.get_bank_ids(hwl.banks[layout.SFX_UNIVERSAL_BANK], hwl.spu_addrs)
                | self._validator.get_bank_ids(hwl.banks[paired], hwl.spu_addrs)
            )

            missing = sorted(
                sid for sid in required
                if 0 <= sid < n_spu and sid not in available
            )

            if missing:
                out.append(Finding(
                    Severity.WARNING, Category.SAMPLE_REFERENCE, Target(TargetKind.SONG, song_index),
                    f"{name} uses sample(s) {missing} not found in its level bank "
                    f"({self._bank_label(paired)}) or the SFX bank. They will be "
                    f"silent in game unless another loaded bank provides them.",
                ))

        return out

    def _check_bank_parsing(self, hwl: HowlFile) -> list[Finding]:
        out: list[Finding] = []
        for i, blob in enumerate(hwl.banks):
            try:
                self._bank_reader.parse(blob, hwl.spu_addrs)
            except Exception as e:
                out.append(Finding(
                    Severity.ERROR, Category.UNREADABLE_BANK, Target(TargetKind.BANK, i),
                    f"{self._bank_label(i)} could not be parsed: {e}",
                ))

        return out

    def _check_bank_slicing(self, hwl: HowlFile) -> list[Finding]:
        """A bank's samples are delimited by the shared SPU size table, so a
        sample resized on behalf of another bank leaves this one being cut at
        offsets its bytes don't match. The slices stop being valid VAG, which
        is what this reports."""
        out: list[Finding] = []

        for i, blob in enumerate(hwl.banks):
            try:
                result = self._slices.validate(blob, hwl.spu_addrs)
            except Exception:
                continue

            if result.is_valid:
                continue

            out.append(Finding(
                Severity.ERROR, Category.BANK_SLICING, Target(TargetKind.BANK, i),
                f"{self._bank_label(i)}: {result.corrupted_count} of "
                f"{result.declared_count} samples are cut at the wrong offset"
                f"{self._slice_origin(result)}. This bank's audio data no longer "
                f"matches the sample sizes it is read with — most likely a sample it "
                f"shares was resized while being replaced in another bank. In game "
                f"these samples play as noise.",
            ))

        return out

    def _slice_origin(self, result) -> str:
        first = result.first_bad
        if first is None:
            return ""

        return f", starting at slot {first.slot} (SPU {first.spu_index})"

    def _check_level_residency(self, hwl: HowlFile) -> list[Finding]:
        """For each stock race track, the samples resident together (SFX bank +
        level bank + the 8-driver shared bank) must fit SPU RAM. Only race tracks
        load that trio; arenas, menus, boss races and the isolated special levels
        load bespoke, lighter sets, so checking them with this model would raise
        false positives — they are left out."""
        out: list[Finding] = []
        flagged: set[int] = set()

        for song_index in range(len(hwl.songs)):
            if not self._layout.is_race_track_song(song_index):
                continue

            paired = self._layout.paired_bank(song_index)
            if paired is None or paired in flagged:
                continue

            context = [layout.SFX_UNIVERSAL_BANK, paired, layout.EIGHT_DRIVER_SHARED_BANK]
            blobs = {b: hwl.banks[b] for b in context if 0 <= b < len(hwl.banks)}
            if paired not in blobs:
                continue

            res = self._residency.residency(hwl.spu_addrs, blobs)
            if res.fits and not res.too_many_banks:
                continue

            flagged.add(paired)
            out.append(Finding(
                Severity.WARNING, Category.SPU_RESIDENCY, Target(TargetKind.BANK, paired),
                f"{self._bank_label(paired)}: the samples a race loads together "
                f"(banks {sorted(blobs)}) total {res.total_bytes} bytes — "
                f"{res.over_by} over the {constants.SPU_USABLE_SAMPLE_BYTES}-byte SPU "
                f"limit. Samples that don't fit go silent in game.",
            ))

        return out

    def _check_file_size(self, hwl, howl_file_size, iso_budget_bytes) -> list[Finding]:
        check = self._howl_size.check(howl_file_size, iso_budget_bytes)
        if check.within_limit:
            return []

        return [Finding(
            Severity.ERROR, Category.HOWL_SIZE, Target(TargetKind.FILE),
            f"The file is {check.current_bytes} bytes ({check.current_sectors} disc "
            f"sectors) — {check.over_sectors} sector(s) larger than the original "
            f"({check.original_sectors}). On disc this shifts every file after it; "
            f"rebuild the ISO after saving or reduce the file's size.",
        )]

    def _summary(self, hwl: HowlFile, howl_file_size: int) -> Finding:
        sample_bytes = sum(e.byte_size for e in hwl.spu_addrs)
        return Finding(
            Severity.INFO, Category.SUMMARY, Target(TargetKind.FILE),
            f"{len(hwl.banks)} banks, {len(hwl.songs)} songs, "
            f"{len(hwl.spu_addrs)} samples ({sample_bytes} bytes total). "
            f"File size {howl_file_size} bytes.",
        )

    def _bank_label(self, index: int) -> str:
        name = self._bank_reader.get_name(index)
        return f"Bank {index} ({name})" if name else f"Bank {index}"

    def _song_label(self, index: int) -> str:
        name = self._cseq_reader.get_name(index)
        return f"Song {index} ({name})" if name else f"Song {index}"
