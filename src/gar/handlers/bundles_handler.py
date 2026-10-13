"""Unity AssetBundle handler.

Sniffs the UnityFS signature and walks the bundle's internal directory,
yielding one Entry per serialized object. This is a *reader*, not a
decoder — the payload is handed to the mesh/texture processors.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator

import lz4.block as lz4

from gar.handlers.base import IngestHandler
from gar.models.entries import Entry
from gar.models.signatures import UNITYFS_MAGIC
from gar.utils.bounds import checked_slice
from gar.utils.blob import BlobReader


class BundleFormatError(ValueError):
    pass


class BundlesHandler(IngestHandler):
    name = "unity-bundle"
    priority = 90
    signatures = (UNITYFS_MAGIC,)

    def iter_entries(self, blob: BlobReader) -> Iterator[Entry]:
        header = blob.peek(64)
        # UnityFS\0 <ver u32> <min_player str> <engine str> <size i64> ...
        cur = len(UNITYFS_MAGIC) + 1
        _ver, = struct.unpack_from(">I", header, cur)
        cur += 4
        for _ in range(2):
            slen = header[cur]
            cur += 1 + slen
        total, comp_blocks, uncomp_blocks, flags = struct.unpack_from(">qiII", header, cur)

        payload = checked_slice(blob, 0, total)
        if flags & 0x80:  # LZ4HC
            payload = lz4.decompress(payload[-comp_blocks:], uncompressed_size=uncomp_blocks)

        yield from self._walk_directory(payload)

    def _walk_directory(self, payload: bytes) -> Iterator[Entry]:
        # Compressed-bytes directory at tail: we scan for the object table
        # marker. Real impl uses the block-info table; this is the fast path.
        marker = b"#OBJECTS#"
        idx = payload.rfind(marker)
        if idx < 0:
            raise BundleFormatError("no object table found")
        count, = struct.unpack_from(">i", payload, idx + len(marker))
        cur = idx + len(marker) + 4
        for _ in range(count):
            path_len, = struct.unpack_from(">i", payload, cur)
            cur += 4
            name = payload[cur : cur + path_len].decode("utf-8", "replace")
            cur += path_len
            off, size, cls = struct.unpack_from(">qii", payload, cur)
            cur += 16
            yield Entry(
                name=name,
                kind=_class_to_kind(cls),
                offset=off,
                size=size,
                uncompressed_size=size,
                compression=0,
                meta={"class_id": cls},
            )


def _class_to_kind(cls: int) -> str:
    return {
        28: "texture",   # Texture2D
        43: "mesh",      # Mesh
        83: "audio",     # AudioClip
        1: "asset",      # GameObject
        114: "asset",    # MonoBehaviour
    }.get(cls, "unknown")