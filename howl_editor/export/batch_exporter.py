# coding: utf-8

from dataclasses import dataclass
from pathlib import Path

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.ctr.analysis.sample_classifier import SampleClassifier, SampleType
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.midi.exporter import CseqMidiExporter, HAS_MIDO
from howl_editor.ps1.formats.vag.decoder import VagDecoder
from howl_editor.ps1.formats.vag.models import VagSample
from howl_editor.ps1.formats.vag.writer import VagWriter


@dataclass
class BatchExportResult:
    banks: int = 0
    songs: int = 0
    midis: int = 0
    samples: int = 0


class BatchExporter:

    def __init__(
        self,
        bank_reader: BankReader,
        cseq_reader: CseqReader,
        vag_writer: VagWriter,
        vag_decoder: VagDecoder,
        sample_classifier: SampleClassifier,
        midi_exporter: CseqMidiExporter,
    ):
        self._bank_reader = bank_reader
        self._cseq_reader = cseq_reader
        self._vag_writer = vag_writer
        self._vag_decoder = vag_decoder
        self._classifier = sample_classifier
        self._midi_exporter = midi_exporter

    def export(
        self, hwl: HowlFile, output_dir: Path, wav_sample_rate: int = 11025,
    ) -> BatchExportResult:
        result = BatchExportResult()
        output_dir = Path(output_dir)

        self._export_banks(hwl, output_dir / HowlCollection.BANKS, result)
        self._export_songs(hwl, output_dir / HowlCollection.SONGS, result)
        self._export_samples(hwl, output_dir / "samples", result, wav_sample_rate)

        return result

    def _export_banks(self, hwl: HowlFile, path: Path, result: BatchExportResult) -> None:
        path.mkdir(parents=True, exist_ok=True)

        for i, bank in enumerate(hwl.banks):
            name = self._bank_reader.get_name(i)
            label = self._safe_filename(name) if name else f"{i:02d}"
            (path / f"Bank_{label}.bnk").write_bytes(bank)
            result.banks += 1

    def _export_songs(self, hwl: HowlFile, path: Path, result: BatchExportResult) -> None:
        path.mkdir(parents=True, exist_ok=True)

        for i, song in enumerate(hwl.songs):
            name = self._cseq_reader.get_name(i)
            label = self._safe_filename(name) if name else f"{i:02d}"
            (path / f"Song_{label}.cseq").write_bytes(song)
            result.songs += 1

            if HAS_MIDO:
                try:
                    cseq = self._cseq_reader.read(song)

                    for j in range(len(cseq.songs)):
                        suffix = f"_Seq{j}" if len(cseq.songs) > 1 else ""
                        midi_path = path / f"Song_{label}{suffix}.mid"
                        self._midi_exporter.export_to_file(cseq, midi_path, j)
                        result.midis += 1
                except Exception:
                    continue

    def _export_samples(
        self, hwl: HowlFile, path: Path, result: BatchExportResult,
        wav_sample_rate: int = 11025,
    ) -> None:
        classification = self._classifier.classify(hwl)
        exported: set[int] = set()

        for bank_blob in hwl.banks:
            try:
                samples = self._bank_reader.parse(bank_blob, hwl.spu_addrs)
            except Exception:
                continue

            for sample in samples:
                if sample.spu_index in exported:
                    continue

                exported.add(sample.spu_index)
                types = classification.get(sample.spu_index, {SampleType.UNKNOWN})
                subdir = self._type_subdir(types)
                sample_dir = path / subdir
                sample_dir.mkdir(parents=True, exist_ok=True)

                name = f"Sample_{sample.spu_index:03d}"
                self._vag_writer.write_file(
                    VagSample(data=sample.data),
                    sample_dir / f"{name}.vag",
                )

                wav = self._vag_decoder.decode_to_wav(sample.data, wav_sample_rate)
                (sample_dir / f"{name}.wav").write_bytes(wav)

                result.samples += 1

    def _type_subdir(self, types: set[SampleType]) -> str:
        if SampleType.INSTRUMENT in types:
            return "instruments"

        if SampleType.PERCUSSION in types:
            return "percussion"
        
        if SampleType.SOUND_EFFECT in types:
            return "effects"
        
        return "other"

    def _safe_filename(self, name: str) -> str:
        return name.replace(" ", "_").replace(":", "").replace("/", "_").replace("\\", "_")
