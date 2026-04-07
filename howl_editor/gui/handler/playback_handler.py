# coding: utf-8

from struct import pack

from PySide6.QtWidgets import QApplication

_WAV_HEADER_SIZE = 36
_WAV_FORMAT_PCM = 1
_WAV_BITS = 16


class PlaybackHandler:

    def __init__(self, window):
        self._window = window

    def can_play(self) -> bool:
        return self._window._audio_player is not None and self._window._audio_player.available

    def stop(self) -> None:
        if self._window._audio_player:
            self._window._audio_player.stop()
            self._window.status.showMessage("Playback stopped")

        if hasattr(self._window, "player_widget"):
            self._window.player_widget.clear()

    def play_sample(self, bank_index: int, sample_index: int) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            samples = self._window._bank_reader.parse(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
            )
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            wav = self._window._vag_decoder.decode_to_wav(sample.data)
            label = f"SPU {sample.spu_index}"

            self._play_wav(
                wav, label, lambda: self.play_sample(bank_index, sample_index),
                update_waveform=False,
            )
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_sequence(self, song_index: int, seq_index: int) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            cseq = self._window._cseq_reader.read(self._window.hwl.songs[song_index])
            if seq_index >= len(cseq.songs):
                return

            sample_data = self._collect_song_samples(cseq)

            self._window.status.showMessage(f"Rendering song {song_index} sequence {seq_index}...")
            QApplication.processEvents()

            pcm = self._window._cseq_renderer.render_song(cseq, seq_index, sample_data)
            wav = self._pcm_to_wav(pcm, sample_rate=22050, channels=2)
            label = f"Song {song_index} Seq {seq_index}"

            self._play_wav(wav, label, lambda: self.play_sequence(song_index, seq_index))
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
            self._show_no_audio()
            return

        try:
            data = self._find_sample_data(spu_index)
            if data is None:
                self._window.status.showMessage(f"SPU {spu_index} not found in any bank")
                return

            sample_rate = int(pitch / 4096 * 44100) if pitch > 0 else 11025
            wav = self._window._vag_decoder.decode_to_wav(data, sample_rate)

            self._play_wav(
                wav, f"{label} (SPU {spu_index}, {sample_rate} Hz)",
                update_waveform=False,
            )
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def _play_wav(
        self, wav: bytes, label: str, replay_callback=None, update_waveform: bool = True,
    ) -> None:
        """Common path: play WAV, update player bar, optionally show waveform."""
        self._window._audio_player.play_wav(wav)
        self._window.status.showMessage(f"Playing {label}")

        if hasattr(self._window, "player_widget"):
            self._window.player_widget.set_now_playing(label, replay_callback)

        if update_waveform and hasattr(self._window, "waveform"):
            self._window.waveform.set_wav(wav)
            self._window.waveform.setVisible(True)

    def _show_no_audio(self) -> None:
        if not self.can_play():
            self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")

    def _pcm_to_wav(self, pcm: bytes, sample_rate: int, channels: int) -> bytes:
        """Wrap raw PCM bytes in a WAV header."""
        byte_rate = sample_rate * channels * _WAV_BITS // 8
        block_align = channels * _WAV_BITS // 8
        header = pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", _WAV_HEADER_SIZE + len(pcm), b"WAVE",
            b"fmt ", 16, _WAV_FORMAT_PCM, channels,
            sample_rate, byte_rate, block_align, _WAV_BITS,
            b"data", len(pcm),
        )

        return header + pcm

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
