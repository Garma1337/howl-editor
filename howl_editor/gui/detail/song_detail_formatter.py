# coding: utf-8

from howl_editor.cseq.reader import CseqReader
from howl_editor.models import HowlFile


class SongDetailFormatter:

    def __init__(self, cseq_reader: CseqReader):
        self._cseq_reader = cseq_reader

    def format_summary(self, hwl: HowlFile) -> str:
        total = sum(len(s) for s in hwl.songs)
        lines = [
            f"Songs ({len(hwl.songs)})", "=" * 50,
            f"Total: {total:,} bytes ({total / 1024:.1f} KB)", "",
            f"{'Idx':>4}  {'Inst':>5}  {'Perc':>5}  {'Seqs':>5}  {'Size':>8}  Name", "-" * 55,
        ]

        for i, song in enumerate(hwl.songs):
            info = self._cseq_reader.get_info(song)
            name = self._cseq_reader.get_name(i)
            label = f"  {name}" if name else ""
            lines.append(f"{i:>4}  {info.num_instruments:>5}  {info.num_percussions:>5}  {info.num_songs:>5}  {info.file_size:>8}{label}")

        return "\n".join(lines)

    def format_tree_info(self, song_data: bytes) -> str:
        info = self._cseq_reader.get_info(song_data)
        if info.file_size == 0:
            return f"{len(song_data):,} bytes"
        return f"{info.num_instruments}i/{info.num_percussions}p, {info.num_songs} seq"

    def format_details(self, hwl: HowlFile, index: int) -> str:
        data = hwl.songs[index]
        name = self._cseq_reader.get_name(index)
        header = f"Song {index}" + (f" - {name}" if name else "")
        lines = [header, "=" * 50, f"Raw size: {len(data):,} bytes"]

        try:
            parsed = self._cseq_reader.read(data)
            lines.append(f"Instruments: {len(parsed.instruments)}")
            lines.append(f"Percussions: {len(parsed.percussions)}")
            lines.append(f"Sequences: {len(parsed.songs)}")

            if parsed.instruments:
                lines += ["", "Instruments:"]
                lines.append(f"  {'#':>3}  {'Vol':>4}  {'Freq':>6}  {'Hz':>7}  {'SPU':>5}  {'ADSR':>10}")

                for i, inst in enumerate(parsed.instruments):
                    lines.append(f"  {i:>3}  {inst.volume:>4}  {inst.frequency:>6}  {inst.freq_hz:>7}  {inst.sample_id:>5}  {inst.adsr:#010x}")

            if parsed.percussions:
                lines += ["", "Percussions:"]
                lines.append(f"  {'#':>3}  {'Vol':>4}  {'Freq':>6}  {'Hz':>7}  {'SPU':>5}")

                for i, p in enumerate(parsed.percussions):
                    lines.append(f"  {i:>3}  {p.volume:>4}  {p.frequency:>6}  {p.freq_hz:>7}  {p.sample_id:>5}")

            for si, song in enumerate(parsed.songs):
                lines.append(f"\nSequence {si}: BPM={song.bpm}, TPQN={song.tpqn}, {len(song.tracks)} tracks")

                for ti, t in enumerate(song.tracks):
                    kind = "drum" if t.is_drum else "melodic"
                    lines.append(f"  Track {ti} ({kind}): {len(t.events)} events, inst={t.instrument}")
        except Exception as e:
            lines.append(f"\nParse error: {e}")

        return "\n".join(lines)
