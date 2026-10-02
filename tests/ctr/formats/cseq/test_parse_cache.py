# coding: utf-8

import pytest

from howl_editor.core.blob_cache import BlobCache
from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.cseq.parse_cache import CseqParseCache
from tests.conftest import build_cseq_bytes


class CountingReader:
    def __init__(self, reader):
        self._reader = reader
        self.reads = 0

    def read(self, blob):
        self.reads += 1
        return self._reader.read(blob)


@pytest.fixture
def counting(cseq_reader):
    return CountingReader(cseq_reader)


@pytest.fixture
def parses(counting):
    return CseqParseCache(counting, BlobCache())


class TestSharedParse:

    def test_repeated_reads_of_one_song_parse_once(self, parses, counting):
        blob = build_cseq_bytes(instruments=[CseqInstrument(sample_id=3)])

        for _ in range(5):
            parses.read(blob)

        assert counting.reads == 1

    def test_callers_see_the_same_parse(self, parses):
        blob = build_cseq_bytes(instruments=[CseqInstrument(sample_id=3)])

        assert parses.read(blob) is parses.read(blob)

    def test_an_edited_song_is_reparsed(self, parses, counting):
        first = build_cseq_bytes(instruments=[CseqInstrument(sample_id=3)])
        edited = build_cseq_bytes(instruments=[CseqInstrument(sample_id=4)])

        parses.read(first)
        parses.read(edited)

        assert counting.reads == 2

    def test_the_parse_is_correct(self, parses):
        blob = build_cseq_bytes(instruments=[CseqInstrument(sample_id=7, frequency=2048)])

        cseq = parses.read(blob)

        assert [i.sample_id for i in cseq.instruments] == [7]
        assert cseq.instruments[0].frequency == 2048
