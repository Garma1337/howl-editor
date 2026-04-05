# coding: utf-8

from struct import unpack_from

from howl_editor.models import HowlFile, CseqInfo
from howl_editor.cseq.reader import CseqReader


class DetailFormatter:

    def __init__(self, cseq_reader: CseqReader):
        self._cseq_reader = cseq_reader

    def howl_details(self, hwl: HowlFile, file_path: str | None) -> str:
        lines = [
            "HOWL File", "=" * 40,
            f"Version:     {hwl.version} ({hwl.version:#x})",
            f"Reserved 1:  {hwl.reserved1}",
            f"Reserved 2:  {hwl.reserved2}",
            f"SPU Entries:  {len(hwl.spu_addrs)}",
            f"Effects:     {len(hwl.other_fx)}",
            f"Engine FX:   {len(hwl.engine_fx)}",
            f"Banks:       {len(hwl.banks)}",
            f"Songs:       {len(hwl.songs)}",
            f"\nHeader data size: {hwl.header_data_size} bytes",
        ]
        
        if file_path:
            lines.append(f"File: {file_path}")

        return "\n".join(lines)

    def spu_table(self, hwl: HowlFile) -> str:
        lines = [f"SPU Address Table ({len(hwl.spu_addrs)} entries)", "=" * 50]
        lines.append(f"{'Index':>6}  {'Ptr':>6}  {'Size':>6}  {'Bytes':>8}")
        lines.append("-" * 35)
        
        for i, e in enumerate(hwl.spu_addrs):
            lines.append(f"{i:>6}  {e.ptr:>6}  {e.size:>6}  {e.byte_size:>8}")
        
        return "\n".join(lines)

    def effects_table(self, hwl: HowlFile) -> str:
        lines = [f"Effects / OtherFX ({len(hwl.other_fx)} entries)", "=" * 60]
        lines.append(f"{'Idx':>4}  {'Flags':>5}  {'Vol':>4}  {'Pitch':>6}  {'SPU':>5}  {'Dur':>5}")
        lines.append("-" * 40)
        
        for i, fx in enumerate(hwl.other_fx):
            lines.append(f"{i:>4}  {fx.flags:>5}  {fx.volume:>4}  {fx.pitch:>6}  {fx.spu_index:>5}  {fx.duration:>5}")
        
        return "\n".join(lines)

    def engine_fx_table(self, hwl: HowlFile) -> str:
        lines = [f"Engine FX ({len(hwl.engine_fx)} entries)", "=" * 50]
        lines.append(f"{'Idx':>4}  {'Flags':>5}  {'Vol':>4}  {'Pitch':>6}  {'Unk':>5}  {'SPU':>5}")
        lines.append("-" * 40)
        
        for i, fx in enumerate(hwl.engine_fx):
            lines.append(f"{i:>4}  {fx.flags:>5}  {fx.volume:>4}  {fx.pitch:>6}  {fx.unk:>5}  {fx.spu_index:>5}")
        
        return "\n".join(lines)

    def banks_summary(self, hwl: HowlFile) -> str:
        total = sum(len(b) for b in hwl.banks)
        lines = [f"Banks ({len(hwl.banks)})", "=" * 50, f"Total: {total:,} bytes ({total / 1024:.1f} KB)", ""]
        lines.append(f"{'Idx':>4}  {'Samples':>8}  {'Size':>10}")
        lines.append("-" * 30)
        
        for i, bank in enumerate(hwl.banks):
            ns = self._bank_sample_count(bank)
            lines.append(f"{i:>4}  {ns:>8}  {len(bank):>10,}")
        
        return "\n".join(lines)

    def bank_summary(self, bank_data: bytes) -> str:
        ns = self._bank_sample_count(bank_data)
        return f"{ns} samples, {len(bank_data)} bytes" if ns > 0 else f"{len(bank_data)} bytes"

    def bank_details(self, hwl: HowlFile, index: int) -> str:
        bank = hwl.banks[index]
        lines = [f"Bank {index}", "=" * 50, f"Size: {len(bank):,} bytes"]
        
        if len(bank) >= 2:
            ns = unpack_from("<H", bank, 0)[0]
            lines.append(f"Samples: {ns}")
        
            if ns < 1024 and len(bank) >= 2 + ns * 2:
                ids = [unpack_from("<h", bank, 2 + i * 2)[0] for i in range(ns)]
                lines.append(f"Sample IDs: {ids}")
                lines.append("")
                lines.append(f"{'#':>4}  {'SPU ID':>7}  {'Size':>6}  {'Bytes':>8}")
                lines.append("-" * 35)
            
                for i, sid in enumerate(ids):
                    if 0 <= sid < len(hwl.spu_addrs):
                        e = hwl.spu_addrs[sid]
                        lines.append(f"{i:>4}  {sid:>7}  {e.size:>6}  {e.byte_size:>8}")
                    else:
                        lines.append(f"{i:>4}  {sid:>7}  {'?':>6}  {'?':>8}")
        
        return "\n".join(lines)

    def songs_summary(self, hwl: HowlFile) -> str:
        total = sum(len(s) for s in hwl.songs)
        lines = [f"Songs ({len(hwl.songs)})", "=" * 50, f"Total: {total:,} bytes ({total / 1024:.1f} KB)", ""]
        lines.append(f"{'Idx':>4}  {'Inst':>5}  {'Perc':>5}  {'Seqs':>5}  {'Size':>8}")
        lines.append("-" * 35)
        
        for i, song in enumerate(hwl.songs):
            info = self._cseq_reader.get_info(song)
            lines.append(f"{i:>4}  {info.num_instruments:>5}  {info.num_percussions:>5}  {info.num_songs:>5}  {info.file_size:>8}")
        
        return "\n".join(lines)

    def song_summary(self, song_data: bytes) -> str:
        info = self._cseq_reader.get_info(song_data)
        if info.file_size == 0:
            return f"{len(song_data)} bytes"
        
        return f"{info.num_instruments}i/{info.num_percussions}p, {info.num_songs} seq"

    def song_details(self, hwl: HowlFile, index: int) -> str:
        data = hwl.songs[index]
        lines = [f"Song {index}", "=" * 50, f"Raw size: {len(data):,} bytes"]
        
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

    def _bank_sample_count(self, data: bytes) -> int:
        if len(data) < 2:
            return 0

        count = unpack_from("<H", data, 0)[0]
        return count if count < 1024 else 0
