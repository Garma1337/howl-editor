# coding: utf-8

import math
import re
from pathlib import Path

from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr.sample_lookup import SampleLookup
from howl_editor.ps1 import spu
from howl_editor.ps1.formats.vag.decoder import VagDecoder

_NEUTRAL_KEY = 60


class SfzExporter:

    def __init__(
        self,
        cseq_reader: CseqReader,
        bank_reader: BankReader,
        sample_lookup: SampleLookup,
        vag_decoder: VagDecoder,
    ):
        self._cseq_reader = cseq_reader
        self._bank_reader = bank_reader
        self._sample_lookup = sample_lookup
        self._vag_decoder = vag_decoder

    def export(
        self, hwl: HowlFile, song_index: int, sfz_path: Path,
        wav_sample_rate: int,
    ) -> int:
        """Write an SFZ patch for one song plus the WAVs it references.

        sfz_path names the .sfz file itself; the sibling 'samples' folder is
        created alongside it. Returns the number of unique samples written.
        """
        sfz_path = Path(sfz_path)
        sfz_path.parent.mkdir(parents=True, exist_ok=True)
        samples_dir = sfz_path.parent / "samples"
        samples_dir.mkdir(exist_ok=True)

        cseq = self._cseq_reader.read(hwl.songs[song_index])

        sample_blobs = self._collect_referenced_samples(
            hwl, cseq.instruments, cseq.percussions,
        )
        written_files = self._write_sample_wavs(sample_blobs, samples_dir, wav_sample_rate)

        song_name = self._cseq_reader.get_name(song_index) or f"song_{song_index}"
        text = self._build_sfz_text(
            song_name, cseq.instruments, cseq.percussions, written_files,
        )
        sfz_path.write_text(text, encoding="utf-8")

        return len(written_files)

    def _collect_referenced_samples(
        self, hwl: HowlFile, instruments, percussions,
    ) -> dict[int, bytes]:
        """Map SPU index → raw VAG bytes for every sample the song touches.
        Deduplicated so a sample shared between instruments / percussion is
        written once."""
        ids: set[int] = set()
        for inst in instruments:
            ids.add(inst.sample_id)
        for perc in percussions:
            ids.add(perc.sample_id)

        out: dict[int, bytes] = {}

        for spu_index in ids:
            data = self._sample_lookup.find_sample_data(hwl, spu_index)

            if data is not None:
                out[spu_index] = data

        return out

    def _write_sample_wavs(
        self, sample_blobs: dict[int, bytes], samples_dir: Path,
        wav_sample_rate: int,
    ) -> dict[int, str]:
        """Decode each unique sample to WAV and write it. Returns a map of
        SPU index → relative WAV filename for SFZ region references."""
        out: dict[int, str] = {}

        for spu_index, data in sample_blobs.items():
            filename = f"SPU_{spu_index:04d}.wav"
            wav = self._vag_decoder.decode_to_wav(data, wav_sample_rate)
            (samples_dir / filename).write_bytes(wav)
            out[spu_index] = f"samples/{filename}"

        return out

    def _build_sfz_text(
        self, song_name: str, instruments, percussions,
        sample_paths: dict[int, str],
    ) -> str:
        lines: list[str] = []
        lines.append(f"// CTR Song: {song_name}")
        lines.append(f"// {len(instruments)} melodic instruments · "
                     f"{len(percussions)} percussion entries")
        lines.append("")

        if instruments:
            lines.append("<group> // melodic instruments")
            for i, inst in enumerate(instruments):
                lines.extend(self._instrument_region(i, inst, sample_paths))
            lines.append("")

        if percussions:
            lines.append("<group> // percussion (one entry per drum slot)")
            for i, perc in enumerate(percussions):
                lines.extend(self._percussion_region(i, perc, sample_paths))
            lines.append("")

        return "\n".join(lines)

    def _instrument_region(
        self, index: int, inst, sample_paths: dict[int, str],
    ) -> list[str]:
        path = sample_paths.get(inst.sample_id)
        if path is None:
            return [f"// instrument {index}: SPU #{inst.sample_id} not found in any bank"]

        tune = self._frequency_to_tune_cents(inst.frequency)
        volume = self._byte_to_decibels(inst.volume)

        block = [
            f"<region> // instrument {index}",
            f"sample={path}",
            f"pitch_keycenter={_NEUTRAL_KEY}",
        ]

        if tune != 0:
            block.append(f"tune={tune}")

        if volume is not None:
            block.append(f"volume={volume:.2f}")

        return block

    def _percussion_region(
        self, index: int, perc, sample_paths: dict[int, str],
    ) -> list[str]:
        path = sample_paths.get(perc.sample_id)
        if path is None:
            return [f"// percussion {index}: SPU #{perc.sample_id} not found in any bank"]

        key = index
        tune = self._frequency_to_tune_cents(perc.frequency)
        volume = self._byte_to_decibels(perc.volume)

        block = [
            f"<region> // percussion {index}",
            f"sample={path}",
            f"key={key}",
            f"pitch_keycenter={key}",
        ]

        if tune != 0:
            block.append(f"tune={tune}")

        if volume is not None:
            block.append(f"volume={volume:.2f}")

        return block

    def _frequency_to_tune_cents(self, frequency: int) -> int:
        """Translate a CSEQ pitch register value into SFZ's `tune` (cents).
        spu.FREQUENCY_UNIT (4096) is the no-shift baseline; doubling that
        value shifts up one octave (+1200 cents)."""
        if frequency <= 0:
            return 0

        ratio = frequency / spu.FREQUENCY_UNIT

        if ratio <= 0:
            return 0

        return int(round(math.log2(ratio) * 1200))

    def _byte_to_decibels(self, byte_volume: int) -> float | None:
        """Map the 0-255 CSEQ volume byte onto SFZ's dB-attenuated volume
        field. SFZ `volume` of 0 = unity gain; -inf = silence. We use
        log-scaled dB so the perceptual loudness curve matches CTR's
        mostly-byte-linear pipeline reasonably closely."""
        if byte_volume <= 0:
            return -144.0  # SFZ's effective silence floor.

        if byte_volume >= 255:
            return 0.0

        return 20 * math.log10(byte_volume / 255)

    @staticmethod
    def safe_filename_stem(name: str) -> str:
        """Strip filesystem-hostile characters so song names can become
        filename stems without surprises (Windows is the strictest)."""
        return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "song"
