# coding: utf-8

from PySide6.QtWidgets import QApplication


class PlaybackHandler:

    def __init__(self, window):
        self._window = window

    def can_play(self) -> bool:
        return self._window._audio_player is not None and self._window._audio_player.available

    def stop(self) -> None:
        if self._window._audio_player:
            self._window._audio_player.stop()
            self._window.status.showMessage("Playback stopped")

    def play_sample(self, bank_index: int, sample_index: int) -> None:
        if not self._window.hwl:
            return

        if not self.can_play():
            self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")
            return

        try:
            samples = self._window._bank_reader.parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            wav = self._window._vag_decoder.decode_to_wav(sample.data)
            self._window._audio_player.play_wav(wav)
            self._window.status.showMessage(f"Playing SPU {sample.spu_index}")
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_sequence(self, song_index: int, seq_index: int) -> None:
        if not self._window.hwl:
            return

        if not self.can_play():
            self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")
            return

        try:
            cseq = self._window._cseq_reader.read(self._window.hwl.songs[song_index])
            if seq_index >= len(cseq.songs):
                return

            sample_data = self._collect_song_samples(cseq)

            self._window.status.showMessage(f"Rendering song {song_index} sequence {seq_index}...")
            QApplication.processEvents()

            wav = self._window._cseq_renderer.render_song_to_wav(cseq, seq_index, sample_data)
            self._window._audio_player.play_wav(wav)
            self._window.status.showMessage(f"Playing song {song_index} sequence {seq_index}")
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_other_fx(self, index: int) -> None:
        if not self._window.hwl or index >= len(self._window.hwl.other_fx):
            return

        fx = self._window.hwl.other_fx[index]
        self._play_fx_sample(fx.spu_index, fx.pitch, f"FX {index}")

    def play_engine_fx(self, index: int) -> None:
        if not self._window.hwl or index >= len(self._window.hwl.engine_fx):
            return

        fx = self._window.hwl.engine_fx[index]
        self._play_fx_sample(fx.spu_index, fx.pitch, f"Engine {index}")

    def _play_fx_sample(self, spu_index: int, pitch: int, label: str) -> None:
        if not self._window.hwl or not self.can_play():
            if not self.can_play():
                self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")
            return

        try:
            data = self._find_sample_data(spu_index)
            if data is None:
                self._window.status.showMessage(f"SPU {spu_index} not found in any bank")
                return

            sample_rate = int(pitch / 4096 * 44100) if pitch > 0 else 11025
            wav = self._window._vag_decoder.decode_to_wav(data, sample_rate)
            self._window._audio_player.play_wav(wav)
            self._window.status.showMessage(f"Playing {label} (SPU {spu_index}, {sample_rate} Hz)")
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def _find_sample_data(self, spu_index: int) -> bytes | None:
        for bank_blob in self._window.hwl.banks:
            try:
                for s in self._window._bank_reader.parse(bank_blob, self._window.hwl.spu_addrs):
                    if s.spu_index == spu_index:
                        return s.data
            except Exception:
                continue
        return None

    def _collect_song_samples(self, cseq) -> dict[int, bytes]:
        needed_ids = set()

        for inst in cseq.instruments:
            needed_ids.add(inst.sample_id)

        for perc in cseq.percussions:
            needed_ids.add(perc.sample_id)

        sample_data: dict[int, bytes] = {}

        for bank_blob in self._window.hwl.banks:
            parsed = self._window._bank_reader.parse(bank_blob, self._window.hwl.spu_addrs)

            for s in parsed:
                if s.spu_index in needed_ids and s.spu_index not in sample_data:
                    sample_data[s.spu_index] = s.data

        return sample_data
