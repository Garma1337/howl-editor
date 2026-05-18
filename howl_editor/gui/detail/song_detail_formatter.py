# coding: utf-8

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.gui.size_formatter import SizeFormatter


class SongDetailFormatter:

    def __init__(
        self,
        cseq_reader: CseqReader,
        template_engine: TemplateEngine,
        size_formatter: SizeFormatter,
    ):
        self._cseq_reader = cseq_reader
        self._template_engine = template_engine
        self._sizes = size_formatter

    def format_summary(self, hwl: HowlFile) -> str:
        total = sum(len(s) for s in hwl.songs)
        songs = [
            {
                "index": str(i),
                "instruments": str(info.num_instruments),
                "percussions": str(info.num_percussions),
                "sequences": str(info.num_songs),
                "size": str(info.file_size),
                "name": self._cseq_reader.get_name(i),
            }
            for i, (song, info) in enumerate(
                (s, self._cseq_reader.get_info(s)) for s in hwl.songs
            )
        ]

        body = self._template_engine.render(
            "song_summary.html",
            count=str(len(hwl.songs)),
            total_bytes=f"{total:,}",
            total_kb=f"{total / 1024:.1f}",
            songs=songs,
        )

        return self._template_engine.render("document.html", body=body)

    def format_tree_info(self, song_data: bytes) -> str:
        info = self._cseq_reader.get_info(song_data)
        if info.file_size == 0:
            return self._sizes.format_bytes(len(song_data))
        return f"{info.num_instruments}i/{info.num_percussions}p, {info.num_songs} seq"

    def format_details(self, hwl: HowlFile, index: int) -> str:
        data = hwl.songs[index]
        name = self._cseq_reader.get_name(index)
        title = f"Song {index}" + (f" - {name}" if name else "")

        try:
            parsed = self._cseq_reader.read(data)
        except Exception as e:
            body = (
                self._template_engine.render("fx_details.html", title=title,
                                             rows=[{"key": "Raw size", "value": self._sizes.format_bytes(len(data))}])
                + f"<p>Parse error: {e}</p>"
            )
            return self._template_engine.render("document.html", body=body)

        instruments = [
            {
                "index": str(i), "volume": str(inst.volume),
                "frequency": str(inst.frequency), "hz": str(inst.freq_hz),
                "sample_id": str(inst.sample_id), "adsr": f"{inst.adsr:#010x}",
            }
            for i, inst in enumerate(parsed.instruments)
        ]

        percussions = [
            {
                "index": str(i), "volume": str(p.volume),
                "frequency": str(p.frequency), "hz": str(p.freq_hz),
                "sample_id": str(p.sample_id),
            }
            for i, p in enumerate(parsed.percussions)
        ]

        sequences = [
            {
                "index": str(si), "bpm": str(song.bpm),
                "tpqn": str(song.tpqn), "track_count": str(len(song.tracks)),
                "tracks": [
                    {
                        "index": str(ti),
                        "type": "drum" if t.is_drum else "melodic",
                        "events": str(len(t.events)),
                        "instrument": str(t.instrument),
                    }
                    for ti, t in enumerate(song.tracks)
                ],
            }
            for si, song in enumerate(parsed.songs)
        ]

        body = self._template_engine.render(
            "song_details.html",
            title=title,
            raw_size=self._sizes.format_bytes(len(data)),
            instrument_count=str(len(parsed.instruments)),
            percussion_count=str(len(parsed.percussions)),
            sequence_count=str(len(parsed.songs)),
            instruments=instruments,
            percussions=percussions,
            sequences=sequences,
        )
        return self._template_engine.render("document.html", body=body)
