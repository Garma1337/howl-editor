# coding: utf-8

from howl_editor.audio.settings.ps1 import PS1_SAMPLE_RATE, PS1_FREQUENCY_UNIT
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.models import HowlFile


class FxDetailFormatter:

    def __init__(self, template_engine: TemplateEngine):
        self._template_engine = template_engine

    def format_effects_table(self, hwl: HowlFile) -> str:
        entries = [
            {"cells": [str(i), str(fx.flags), str(fx.volume), str(fx.pitch), str(fx.spu_index), str(fx.duration)]}
            for i, fx in enumerate(hwl.other_fx)
        ]

        body = self._template_engine.render(
            "fx_table.html",
            title=f"Effects / OtherFX ({len(hwl.other_fx)} entries)",
            headers=["Idx", "Flags", "Vol", "Pitch", "SPU", "Dur"],
            entries=entries,
        )

        return self._template_engine.render("document.html", body=body)

    def format_engine_fx_table(self, hwl: HowlFile) -> str:
        entries = [
            {"cells": [str(i), str(fx.flags), str(fx.volume), str(fx.pitch), str(fx.unk), str(fx.spu_index)]}
            for i, fx in enumerate(hwl.engine_fx)
        ]

        body = self._template_engine.render(
            "fx_table.html",
            title=f"Engine FX ({len(hwl.engine_fx)} entries)",
            headers=["Idx", "Flags", "Vol", "Pitch", "Unk", "SPU"],
            entries=entries,
        )

        return self._template_engine.render("document.html", body=body)

    def format_other_fx_details(self, hwl: HowlFile, index: int) -> str:
        fx = hwl.other_fx[index]
        freq_hz = self._pitch_to_hz(fx.pitch)

        rows = [
            {"key": "Flags", "value": f"{fx.flags} ({fx.flags:#04x})"},
            {"key": "Volume", "value": str(fx.volume)},
            {"key": "Pitch", "value": f"{fx.pitch} ({freq_hz} Hz)"},
            {"key": "SPU Index", "value": str(fx.spu_index)},
            {"key": "Duration", "value": f"{fx.duration} frames"},
        ]

        body = self._template_engine.render("fx_details.html", title=f"OtherFX {index}", rows=rows)
        return self._template_engine.render("document.html", body=body)

    def format_engine_fx_details(self, hwl: HowlFile, index: int) -> str:
        fx = hwl.engine_fx[index]
        freq_hz = self._pitch_to_hz(fx.pitch)
        rows = [
            {"key": "Flags", "value": f"{fx.flags} ({fx.flags:#04x})"},
            {"key": "Volume", "value": str(fx.volume)},
            {"key": "Pitch", "value": f"{fx.pitch} ({freq_hz} Hz)"},
            {"key": "Unknown", "value": str(fx.unk)},
            {"key": "SPU Index", "value": str(fx.spu_index)},
        ]

        body = self._template_engine.render("fx_details.html", title=f"EngineFX {index}", rows=rows)
        return self._template_engine.render("document.html", body=body)

    def _pitch_to_hz(self, pitch: int) -> int:
        if pitch <= 0:
            return 0

        return int(pitch / PS1_FREQUENCY_UNIT * PS1_SAMPLE_RATE)
