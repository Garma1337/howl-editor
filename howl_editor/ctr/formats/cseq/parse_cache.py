# coding: utf-8

from howl_editor.core.blob_cache import BlobCache
from howl_editor.ctr.formats.cseq.models import CseqFile
from howl_editor.ctr.formats.cseq.reader import CseqReader


class CseqParseCache:
    """Shared parses of song blobs for read-only callers.

    Parsing one song costs ~5 ms, and a refresh after a single edit used to
    reparse every song in the file several times over — for diagnostics, for
    sample classification and again for the workshop. This hands all of them
    the same parse.

    The returned CseqFile is SHARED: treat it as read-only. Anything that
    mutates a song must parse it through CseqReader itself, so its changes
    cannot leak into another caller's view of the file."""

    def __init__(self, cseq_reader: CseqReader, blob_cache: BlobCache):
        self._reader = cseq_reader
        self._cache = blob_cache

    def read(self, blob: bytes) -> CseqFile:
        return self._cache.get(blob, self._reader.read)
