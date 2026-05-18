# coding: utf-8

from pathlib import Path

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.ctr.formats.howl.models import HowlFile, OtherFX, EngineFX
from howl_editor.gui.detail.fx_detail_formatter import FxDetailFormatter

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "howl_editor" / "gui" / "templates"


def _formatter():
    return FxDetailFormatter(TemplateEngine(_TEMPLATE_DIR))


def _hwl_with_fx():
    return HowlFile(
        other_fx=[OtherFX(flags=1, volume=128, pitch=4096, spu_index=5, duration=200)],
        engine_fx=[EngineFX(flags=2, volume=64, pitch=8192, unk=99, spu_index=3)],
    )


class TestFxDetailFormatter:

    def test_format_effects_table(self):
        fmt = _formatter()
        text = fmt.format_effects_table(_hwl_with_fx())

        assert "OtherFX" in text
        assert "128" in text

    def test_format_effects_table_empty(self):
        fmt = _formatter()
        text = fmt.format_effects_table(HowlFile())

        assert "0 entries" in text

    def test_format_engine_fx_table(self):
        fmt = _formatter()
        text = fmt.format_engine_fx_table(_hwl_with_fx())

        assert "Engine FX" in text
        assert "64" in text

    def test_format_other_fx_details(self):
        fmt = _formatter()
        text = fmt.format_other_fx_details(_hwl_with_fx(), 0)

        assert "OtherFX 0" in text
        assert "128" in text
        assert "Hz" in text
        assert "200" in text

    def test_format_engine_fx_details(self):
        fmt = _formatter()
        text = fmt.format_engine_fx_details(_hwl_with_fx(), 0)

        assert "EngineFX 0" in text
        assert "64" in text
        assert "Hz" in text

    def test_pitch_to_hz_zero(self):
        fmt = _formatter()
        hwl = HowlFile(other_fx=[OtherFX(pitch=0)])
        text = fmt.format_other_fx_details(hwl, 0)

        assert "(0 Hz)" in text

    def test_pitch_to_hz_conversion(self):
        fmt = _formatter()
        hwl = HowlFile(other_fx=[OtherFX(pitch=4096)])
        text = fmt.format_other_fx_details(hwl, 0)

        assert "44100" in text
