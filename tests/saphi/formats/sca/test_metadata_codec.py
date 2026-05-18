# coding: utf-8

import json

import pytest

from howl_editor.saphi.formats.sca.models import ScaMetadata


class TestEncode:

    def test_emits_utf8_json_with_required_keys(self, sca_metadata_codec):
        raw = sca_metadata_codec.encode(ScaMetadata(name="Breeze Harbor", author="Garma"))
        obj = json.loads(raw.decode("utf-8"))

        assert obj == {"name": "Breeze Harbor", "author": "Garma"}

    def test_preserves_non_ascii(self, sca_metadata_codec):
        # ensure_ascii=False keeps unicode literal (smaller payload, human-readable hex dumps)
        raw = sca_metadata_codec.encode(ScaMetadata(name="Über Pyramid 🎵", author="Søren"))
        obj = json.loads(raw.decode("utf-8"))

        assert obj["name"] == "Über Pyramid 🎵"
        assert obj["author"] == "Søren"


class TestDecode:

    def test_reads_well_formed_metadata(self, sca_metadata_codec):
        raw = b'{"name":"Track","author":"Author"}'

        meta = sca_metadata_codec.decode(raw)

        assert meta.name == "Track"
        assert meta.author == "Author"

    def test_ignores_unknown_keys(self, sca_metadata_codec):
        raw = b'{"name":"Track","author":"Author","bpm":120,"future":"ignored"}'

        meta = sca_metadata_codec.decode(raw)

        assert meta.name == "Track"
        assert meta.author == "Author"

    def test_missing_name_raises(self, sca_metadata_codec):
        with pytest.raises(ValueError, match="missing required keys"):
            sca_metadata_codec.decode(b'{"author":"Author"}')

    def test_missing_author_raises(self, sca_metadata_codec):
        with pytest.raises(ValueError, match="missing required keys"):
            sca_metadata_codec.decode(b'{"name":"Track"}')

    def test_invalid_json_raises(self, sca_metadata_codec):
        with pytest.raises(json.JSONDecodeError):
            sca_metadata_codec.decode(b"not json at all")


class TestRoundTrip:

    @pytest.mark.parametrize("name, author", [
        ("Breeze Harbor", "Boxic"),
        ("", ""),
        ("Track With Spaces", "Multi Word Author"),
        ("Über Pyramid 🎵", "Søren"),
        ('"quoted"', "back\\slash"),
    ])
    def test_round_trip_preserves_fields(self, sca_metadata_codec, name, author):
        original = ScaMetadata(name=name, author=author)
        decoded = sca_metadata_codec.decode(sca_metadata_codec.encode(original))

        assert decoded == original
