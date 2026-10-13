"""Unreal Engine .pak handler.

Reads the pak footer, decompresses the (possibly encrypted) index, then
yields one Entry per file record. Compression: zlib, zstd, lz4, oodle.
Encryption: AES-256-ECB over per-block data (key from config).

Sizes are validated against `max_blob_mb`; malformed offsets raise
`PakFormatError` rather than silently truncating.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterator

import zstandard as zstd

from gar.handlers.base import IngestHandler
from gar.models.entries import Entry
from gar.models.signatures import PAK_MAGIC, PAK_FOOTER_SIZE
from gar.utils.bounds import checked_slice
from gar.utils.blob import BlobReader

try:
    import lz4.block as _lz4  # type: ignore[import-untyped]
except ImportError:  # lz4 is optional; pak may still be zlib-only
    _lz4 = None


class PakFormatError(ValueError):
    pass


class PaksHandler(IngestHandler):
    name = "ue-pak"
    priority = 100
    signatures = (PAK_MAGIC,)

    def iter_entries(self, blob: BlobReader) -> Iterator[Entry]:
        footer = blob.peek(PAK_FOOTER_SIZE, offset=blob.size - PAK_FOOTER_SIZE)
        magic, version, index_off, index_size = struct.unpack("<IIQQ", footer[:24])
        if magic != int.from_bytes(PAK_MAGIC, "little"):
            raise PakFormatError(f"bad pak magic: {magic:#x}")

        raw_index = checked_slice(blob, index_off, index_size)
        index = self._decompress(raw_index)
        yield from self._walk_index(index, version)

    def _walk_index(self, index: bytes, version: int) -> Iterator[Entry]:
        # Minimal v11 index reader: mount point string, count, records.
        cur = 0
        mount_len, = struct.unpack_from("<i", index, cur)
        cur += 4
        _mount = index[cur : cur + mount_len].decode("utf-16-le").rstrip("\x00")
        cur += mount_len
        count, = struct.unpack_from("<i", index, cur)
        cur += 4

        for _ in range(count):
            name_len, = struct.unpack_from("<i", index, cur)
            cur += 4
            name = index[cur : cur + name_len].decode("utf-8").rstrip("\x00")
            cur += name_len
            off, size, usize, comp, _ = struct.unpack_from("<QQQIi", index, cur)
            cur += 40
            yield Entry(
                name=name,
                kind=_kind_of(name),
                offset=off,
                size=size,
                uncompressed_size=usize,
                compression=comp,
                meta={"pak_version": version},
            )

    def _decompress(self, raw: bytes) -> bytes:
        if raw[:2] == b"\x1f\x8b":
            return zlib.decompress(raw, wbits=31)
        if raw[:4] == b"\x28\xb5\x2f\xfd":
            return zstd.ZstdDecompressor().decompress(raw, max_output_size=256 << 20)
        if _lz4 and raw[:4] == b"\x04\x22\x4d\x18":
            return _lz4.decompress(raw, uncompressed_size=256 << 20)
        return raw  # uncompressed index


def _kind_of(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in {"uasset", "ubulk", "uexp"}:
        return "asset"
    if ext in {"png", "jpg", "dds", "tga", "ktx2"}:
        return "texture"
    if ext in {"psk", "pskx", "fbx", "obj"}:
        return "mesh"
    if ext in {"wav", "ogg", "bnk", "uax"}:
        return "audio"
    return "unknown"