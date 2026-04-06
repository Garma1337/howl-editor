# coding: utf-8

from howl_editor.models import HowlFile


class FxDetailFormatter:

    def format_effects_table(self, hwl: HowlFile) -> str:
        lines = [
            f"Effects / OtherFX ({len(hwl.other_fx)} entries)", "=" * 60,
            f"{'Idx':>4}  {'Flags':>5}  {'Vol':>4}  {'Pitch':>6}  {'SPU':>5}  {'Dur':>5}", "-" * 40,
        ]

        for i, fx in enumerate(hwl.other_fx):
            lines.append(f"{i:>4}  {fx.flags:>5}  {fx.volume:>4}  {fx.pitch:>6}  {fx.spu_index:>5}  {fx.duration:>5}")

        return "\n".join(lines)

    def format_engine_fx_table(self, hwl: HowlFile) -> str:
        lines = [
            f"Engine FX ({len(hwl.engine_fx)} entries)", "=" * 50,
            f"{'Idx':>4}  {'Flags':>5}  {'Vol':>4}  {'Pitch':>6}  {'Unk':>5}  {'SPU':>5}", "-" * 40,
        ]

        for i, fx in enumerate(hwl.engine_fx):
            lines.append(f"{i:>4}  {fx.flags:>5}  {fx.volume:>4}  {fx.pitch:>6}  {fx.unk:>5}  {fx.spu_index:>5}")

        return "\n".join(lines)

    def format_other_fx_details(self, hwl: HowlFile, index: int) -> str:
        fx = hwl.other_fx[index]
        freq_hz = int(fx.pitch / 4096 * 44100) if fx.pitch > 0 else 0
        lines = [
            f"OtherFX {index}", "=" * 40,
            f"Flags:      {fx.flags} ({fx.flags:#04x})",
            f"Volume:     {fx.volume}",
            f"Pitch:      {fx.pitch} ({freq_hz} Hz)",
            f"SPU Index:  {fx.spu_index}",
            f"Duration:   {fx.duration} frames",
        ]

        return "\n".join(lines)

    def format_engine_fx_details(self, hwl: HowlFile, index: int) -> str:
        fx = hwl.engine_fx[index]
        freq_hz = int(fx.pitch / 4096 * 44100) if fx.pitch > 0 else 0
        lines = [
            f"EngineFX {index}", "=" * 40,
            f"Flags:      {fx.flags} ({fx.flags:#04x})",
            f"Volume:     {fx.volume}",
            f"Pitch:      {fx.pitch} ({freq_hz} Hz)",
            f"Unknown:    {fx.unk}",
            f"SPU Index:  {fx.spu_index}",
        ]

        return "\n".join(lines)
