# coding: utf-8

from struct import pack

from howl_editor.ctr.formats.howl.models import HowlHeader


class TestDetectRelease:
    def test_release_version(self, version_detector):
        data = pack("<II", HowlHeader.MAGIC, 0x80) + b"\x00" * (HowlHeader.SIZE - 8)
        info = version_detector.detect(data)

        assert info.version_value == 0x80
        assert info.version_name == "Release"
        assert info.is_known is True
        assert info.magic_valid is True

    def test_prototype_version(self, version_detector):
        data = pack("<II", HowlHeader.MAGIC, 0x7D) + b"\x00" * (HowlHeader.SIZE - 8)
        info = version_detector.detect(data)

        assert info.version_name == "Prototype"
        assert info.is_known is True

    def test_demo_versions(self, version_detector):
        for ver, name in [(0x6F, "Demo (Test Drive)"), (0x71, "Demo (OPSM)"), (0x72, "Demo (Spyro)")]:
            data = pack("<II", HowlHeader.MAGIC, ver) + b"\x00" * (HowlHeader.SIZE - 8)
            info = version_detector.detect(data)

            assert info.version_name == name
            assert info.is_known is True


class TestDetectUnknown:

    def test_unknown_version(self, version_detector):
        data = pack("<II", HowlHeader.MAGIC, 0xFF) + b"\x00" * (HowlHeader.SIZE - 8)
        info = version_detector.detect(data)

        assert info.is_known is False
        assert info.magic_valid is True
        assert "Unknown" in info.version_name

    def test_modified_file_accepted(self, version_detector):
        data = pack("<II", HowlHeader.MAGIC, 0x80) + b"\xFF" * (HowlHeader.SIZE - 8)
        info = version_detector.detect(data)

        assert info.magic_valid is True
        assert info.is_known is True


class TestDetectInvalid:

    def test_bad_magic(self, version_detector):
        data = pack("<II", 0xDEADBEEF, 0x80) + b"\x00" * (HowlHeader.SIZE - 8)
        info = version_detector.detect(data)

        assert info.magic_valid is False

    def test_too_small(self, version_detector):
        info = version_detector.detect(b"\x00" * 10)

        assert info.magic_valid is False
        assert info.version_name == "Invalid"

    def test_empty(self, version_detector):
        info = version_detector.detect(b"")

        assert info.magic_valid is False
