# coding: utf-8

import json

from howl_editor.saphi.formats.sca.models import ScaFormat, ScaMetadata


class ScaMetadataCodec:
    """Encodes and decodes ScaMetadata as a UTF-8 JSON object."""

    def encode(self, metadata: ScaMetadata) -> bytes:
        obj = {ScaFormat.META_KEY_NAME: metadata.name, ScaFormat.META_KEY_AUTHOR: metadata.author}
        return json.dumps(obj, ensure_ascii=False).encode(ScaFormat.META_ENCODING)

    def decode(self, raw: bytes) -> ScaMetadata:
        obj = json.loads(raw.decode(ScaFormat.META_ENCODING))

        if ScaFormat.META_KEY_NAME not in obj or ScaFormat.META_KEY_AUTHOR not in obj:
            raise ValueError(f"metadata missing required keys: name, author (got {list(obj)})")

        return ScaMetadata(name=obj[ScaFormat.META_KEY_NAME], author=obj[ScaFormat.META_KEY_AUTHOR])
