# coding: utf-8

from struct import pack, pack_into

import pytest

from howl_editor.analysis.sample_classifier import SampleClassifier
from howl_editor.analysis.validator import BankCseqValidator
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.bank.builder import BankBuilder
from howl_editor.bank.reader import BankReader
from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.howl.editor import HowlEditor
from howl_editor.howl.reader import HowlReader
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.howl.writer import HowlWriter
from howl_editor.models import (
    HowlFile, HowlHeader, SpuAddrEntry, OtherFX, EngineFX, VagSample,
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
)
from howl_editor.models.howl import SECTOR_SIZE, bytes_to_sectors
from howl_editor.vag.reader import VagReader
from howl_editor.vag.writer import VagWriter


@pytest.fixture
def howl_reader():
    return HowlReader()

@pytest.fixture
def howl_writer():
    return HowlWriter()

@pytest.fixture
def howl_editor():
    return HowlEditor()

@pytest.fixture
def vlq_codec():
    return VlqCodec()

@pytest.fixture
def cseq_reader(vlq_codec):
    return CseqReader(vlq_codec)

@pytest.fixture
def cseq_writer(vlq_codec):
    return CseqWriter(vlq_codec)

@pytest.fixture
def vag_reader():
    return VagReader()

@pytest.fixture
def vag_writer():
    return VagWriter()

@pytest.fixture
def bank_reader():
    return BankReader()

@pytest.fixture
def bank_builder(vag_reader):
    return BankBuilder(vag_reader)

@pytest.fixture
def version_detector():
    return HowlVersionDetector()

@pytest.fixture
def vag_decoder():
    return VagDecoder(WavWriter())

@pytest.fixture
def sample_classifier(cseq_reader):
    return SampleClassifier(cseq_reader)

@pytest.fixture
def validator(bank_reader, cseq_reader):
    return BankCseqValidator(bank_reader, cseq_reader)


@pytest.fixture
def empty_howl():
    return HowlFile()

@pytest.fixture
def sample_howl():
    """A HowlFile with some data for testing."""
    return HowlFile(
        spu_addrs=[SpuAddrEntry(0, 100), SpuAddrEntry(0, 200)],
        other_fx=[OtherFX(1, 128, 4096, 0, 100)],
        engine_fx=[EngineFX(1, 200, 8192, 0, 1)],
        banks=[b"\x01\x00\x00\x00" + b"\xAA" * 2044],  # 1 sample, padded to 2048
        songs=[b"\x10\x00\x00\x00\x00\x00\x01\x00" + b"\x00" * 8],  # minimal CSEQ-like blob
    )


def build_hwl_bytes(
    num_spu=0, num_other=0, num_engine=0,
    banks=None, songs=None,
    spu_addrs=None, other_fx=None, engine_fx=None,
    version=HowlHeader.VERSION_RELEASE,
) -> bytes:
    """Build minimal valid HWL binary data from components."""
    banks = banks or []
    songs = songs or []
    spu_addrs = spu_addrs or [SpuAddrEntry(0, 0)] * num_spu
    other_fx = other_fx or [OtherFX()] * num_other
    engine_fx = engine_fx or [EngineFX()] * num_engine

    num_banks = len(banks)
    num_songs = len(songs)
    num_spu = len(spu_addrs)
    num_other = len(other_fx)
    num_engine = len(engine_fx)

    header_data_size = (
        num_spu * 4 + num_other * 8 + num_engine * 8
        + num_banks * 2 + num_songs * 2
    )
    header_bytes = HowlHeader.SIZE + header_data_size
    header_sectors = bytes_to_sectors(header_bytes)

    current_sector = header_sectors
    bank_offsets = []
    for bank in banks:
        bank_offsets.append(current_sector)
        current_sector += bytes_to_sectors(len(bank))

    song_offsets = []
    for song in songs:
        song_offsets.append(current_sector)
        current_sector += bytes_to_sectors(len(song))

    total_bytes = current_sector * SECTOR_SIZE
    buf = bytearray(total_bytes)

    HowlHeader.STRUCT.pack_into(buf, 0,
        HowlHeader.MAGIC, version, 0, 0,
        num_spu, num_other, num_engine,
        num_banks, num_songs, header_data_size)

    pos = HowlHeader.SIZE
    for e in spu_addrs:
        SpuAddrEntry.STRUCT.pack_into(buf, pos, e.ptr, e.size)
        pos += 4
    for fx in other_fx:
        OtherFX.STRUCT.pack_into(buf, pos, fx.flags, fx.volume, fx.pitch, fx.spu_index, fx.duration)
        pos += 8
    for fx in engine_fx:
        EngineFX.STRUCT.pack_into(buf, pos, fx.flags, fx.volume, fx.pitch, fx.unk, fx.spu_index)
        pos += 8
    for off in bank_offsets:
        pack_into("<H", buf, pos, off)
        pos += 2
    for off in song_offsets:
        pack_into("<H", buf, pos, off)
        pos += 2

    for bank, off in zip(banks, bank_offsets):
        start = off * SECTOR_SIZE
        buf[start:start + len(bank)] = bank

    for song, off in zip(songs, song_offsets):
        start = off * SECTOR_SIZE
        buf[start:start + len(song)] = song

    return bytes(buf)


def build_cseq_bytes(
    instruments=None, percussions=None,
    songs=None, bpm=120, tpqn=480,
) -> bytes:
    """Build minimal valid CSEQ binary data."""
    instruments = instruments or []
    percussions = percussions or []

    if songs is None:
        songs = [CseqSong(bpm=bpm, tpqn=tpqn, tracks=[
            CseqTrack(events=[CseqEvent(event_type=CseqEventType.END_TRACK)])
        ])]

    cseq = CseqFile(instruments=instruments, percussions=percussions, songs=songs)
    writer = CseqWriter(VlqCodec())
    return writer.serialize(cseq)


def build_vag_bytes(data: bytes = b"\x00" * 16, sample_rate: int = 44100, name: str = "test") -> bytes:
    """Build VAG file bytes with header."""
    header = bytearray(VagSample.HEADER_SIZE)
    pack_into(">4sIIII", header, 0, VagSample.MAGIC, 3, 0, len(data), sample_rate)
    name_bytes = name.encode("ascii")[:16]
    header[0x20:0x20 + len(name_bytes)] = name_bytes
    return bytes(header) + data


def build_bank_blob(sample_ids: list[int], sample_datas: list[bytes]) -> bytes:
    """Build a bank blob from sample IDs and raw data."""
    header = pack("<H", len(sample_ids))
    for sid in sample_ids:
        header += pack("<h", sid)
    padded_len = bytes_to_sectors(len(header)) * SECTOR_SIZE
    header_padded = header + b"\x00" * (padded_len - len(header))
    return header_padded + b"".join(sample_datas)
