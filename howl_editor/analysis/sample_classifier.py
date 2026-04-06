# coding: utf-8

from enum import Enum

from howl_editor.cseq.reader import CseqReader
from howl_editor.models import HowlFile


class SampleType(Enum):
    INSTRUMENT = "Instrument"
    PERCUSSION = "Percussion"
    SOUND_EFFECT = "SoundEffect"
    UNKNOWN = "Unknown"


class SampleClassifier:

    def __init__(self, cseq_reader: CseqReader):
        self._cseq_reader = cseq_reader

    def classify(self, hwl: HowlFile) -> dict[int, set[SampleType]]:
        result: dict[int, set[SampleType]] = {}

        for fx in hwl.other_fx:
            result.setdefault(fx.spu_index, set()).add(SampleType.SOUND_EFFECT)

        for song_data in hwl.songs:
            try:
                cseq = self._cseq_reader.read(song_data)

                for inst in cseq.instruments:
                    result.setdefault(inst.sample_id, set()).add(SampleType.INSTRUMENT)

                for perc in cseq.percussions:
                    result.setdefault(perc.sample_id, set()).add(SampleType.PERCUSSION)
            except Exception:
                continue

        return result

    def get_label(self, types: set[SampleType]) -> str:
        if not types:
            return ""

        names = sorted(t.value for t in types)
        return ", ".join(names)
