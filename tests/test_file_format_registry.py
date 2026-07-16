# coding: utf-8

from howl_editor.file_format_registry import FileFormatRegistry


class TestCombinedFilter:

    def test_merges_all_extensions_into_one_filter(self):
        result = FileFormatRegistry.create_combined_filter(
            "Sequence Files", FileFormatRegistry.CSEQ, FileFormatRegistry.MIDI,
        )

        assert result == "Sequence Files (*.cseq *.mid *.midi)"

    def test_single_format(self):
        result = FileFormatRegistry.create_combined_filter(
            "Just CSEQ", FileFormatRegistry.CSEQ,
        )

        assert result == "Just CSEQ (*.cseq)"
