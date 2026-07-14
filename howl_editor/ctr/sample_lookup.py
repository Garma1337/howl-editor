# coding: utf-8

from howl_editor.ps1 import spu
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.models import CseqFile
from howl_editor.ctr.formats.howl.models import HowlFile

_DEFAULT_SAMPLE_RATE = 11025


class SampleLookup:
    """Searches HWL data structures to locate sample data and playback rates."""

    def __init__(self, bank_reader: BankReader, cseq_reader: CseqReader):
        self._bank_reader = bank_reader
        self._cseq_reader = cseq_reader

    def find_sample_data(self, hwl: HowlFile, spu_index: int) -> bytes | None:
        """Search all banks for the raw sample data of a given SPU index."""
        for bank_blob in hwl.banks:
            try:
                for s in self._bank_reader.parse(bank_blob, hwl.spu_addrs):
                    if s.spu_index == spu_index:
                        return s.data
            except Exception:
                continue

        return None

    def find_bank_and_sample_index(
        self, hwl: HowlFile, spu_index: int,
    ) -> tuple[int, int] | None:
        """Return (bank_index, sample_slot) for the first bank that contains
        a sample with the requested SPU index."""
        for bank_index, bank_blob in enumerate(hwl.banks):
            try:
                for slot, s in enumerate(self._bank_reader.parse(bank_blob, hwl.spu_addrs)):
                    if s.spu_index == spu_index:
                        return bank_index, slot
            except Exception:
                continue

        return None

    def bank_spu_order(self, hwl: HowlFile, bank_index: int) -> list[int]:
        """Return the SPU indices of a bank's samples in bank order.

        Used to prefill MIDI-import SPU assignments: a music maker who lays out
        their MIDI tracks to mirror a bank's instrument order gets each track
        pointed at the matching sample without looking IDs up by hand. Returns
        an empty list if the bank index is out of range or unreadable."""
        if bank_index < 0 or bank_index >= len(hwl.banks):
            return []

        try:
            return [s.spu_index for s in self._bank_reader.parse(hwl.banks[bank_index], hwl.spu_addrs)]
        except Exception:
            return []

    def collect_song_samples(self, hwl: HowlFile, cseq: CseqFile) -> dict[int, bytes]:
        """Collect all sample data needed by a CSEQ file from the HWL's banks."""
        needed_ids = set()

        for inst in cseq.instruments:
            needed_ids.add(inst.sample_id)

        for perc in cseq.percussions:
            needed_ids.add(perc.sample_id)

        sample_data: dict[int, bytes] = {}

        for bank_blob in hwl.banks:
            try:
                parsed = self._bank_reader.parse(bank_blob, hwl.spu_addrs)

                for s in parsed:
                    if s.spu_index in needed_ids and s.spu_index not in sample_data:
                        sample_data[s.spu_index] = s.data
            except Exception:
                continue

        return sample_data

    def lookup_sample_rate(self, hwl: HowlFile, spu_index: int) -> int:
        """
        Find the playback rate for a sample by checking FX and instrument tables.

        Searches OtherFX, EngineFX, then CSEQ instrument/percussion definitions.
        Returns 11025 Hz if no reference is found.
        """
        for fx in hwl.other_fx:
            if fx.spu_index == spu_index and fx.pitch > 0:
                return self._pitch_to_hz(fx.pitch)

        for fx in hwl.engine_fx:
            if fx.spu_index == spu_index and fx.pitch > 0:
                return self._pitch_to_hz(fx.pitch)

        for song_data in hwl.songs:
            try:
                cseq = self._cseq_reader.read(song_data)

                for inst in cseq.instruments:
                    if inst.sample_id == spu_index and inst.frequency > 0:
                        return self._pitch_to_hz(inst.frequency)

                for perc in cseq.percussions:
                    if perc.sample_id == spu_index and perc.frequency > 0:
                        return self._pitch_to_hz(perc.frequency)
            except Exception:
                continue

        return _DEFAULT_SAMPLE_RATE

    def sample_rate_map(self, hwl: HowlFile) -> dict[int, int]:
        """Build spu_index → playback-rate (Hz) for every sample referenced
        anywhere in the HWL, in one pass.

        Same source priority as `lookup_sample_rate` (OtherFX, then EngineFX,
        then song instruments, then song percussions — first reference wins),
        but resolves the whole file at once so callers like the MIDI-import
        dialog can update a sample's frequency the instant its SPU is picked,
        without re-scanning per lookup. SPUs with no rate reference are simply
        absent from the map."""
        rates: dict[int, int] = {}

        for fx in hwl.other_fx:
            if fx.pitch > 0:
                rates.setdefault(fx.spu_index, self._pitch_to_hz(fx.pitch))

        for fx in hwl.engine_fx:
            if fx.pitch > 0:
                rates.setdefault(fx.spu_index, self._pitch_to_hz(fx.pitch))

        for song_data in hwl.songs:
            try:
                cseq = self._cseq_reader.read(song_data)
            except Exception:
                continue

            for inst in cseq.instruments:
                if inst.frequency > 0:
                    rates.setdefault(inst.sample_id, self._pitch_to_hz(inst.frequency))

            for perc in cseq.percussions:
                if perc.frequency > 0:
                    rates.setdefault(perc.sample_id, self._pitch_to_hz(perc.frequency))

        return rates

    def _pitch_to_hz(self, pitch: int) -> int:
        return int(pitch / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)
