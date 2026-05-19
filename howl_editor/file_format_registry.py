# coding: utf-8

from dataclasses import dataclass


@dataclass(frozen=True)
class FileFormat:
    extensions: tuple[str, ...]
    display_name: str
    file_filter: str

    @property
    def extension(self) -> str:
        """The canonical extension — the one the editor writes by default."""
        return self.extensions[0]


class FileFormatRegistry:
    """Read-only registry of end-user file-format facts.

    Pure data — every consumer uses the same single set of facts, so the
    formats are exposed as class attributes (`FileFormatRegistry.CSEQ`)
    rather than DI-injected instance state.
    """

    CSEQ = FileFormat((".cseq",),         "CSEQ",                  "CSEQ Files (*.cseq)")
    BANK = FileFormat((".bnk",),          "Bank",                  "Bank Files (*.bnk)")
    HOWL = FileFormat((".hwl",),          "HOWL",                  "HOWL Files (*.hwl)")
    VAG  = FileFormat((".vag",),          "VAG",                   "VAG Files (*.vag)")
    SCA  = FileFormat((".sca",),          "Saphi Audio Container", "Saphi Audio Container (*.sca)")
    MIDI = FileFormat((".mid", ".midi"),  "MIDI",                  "MIDI Files (*.mid *.midi)")
    WAV  = FileFormat((".wav",),          "WAV",                   "WAV Files (*.wav)")
    SFZ  = FileFormat((".sfz",),          "SFZ Sampler Patch",     "SFZ Files (*.sfz)")
