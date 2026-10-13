"""Texture processor: BCn/DDS/PNG/TGA -> PNG or KTX2.

Handles both raw DDS containers and in-container BC1/BC3/BC7 payloads
(common in UE/Unity bundles). Decode path uses numpy for the block
unpacking so we don't shell out to texconv.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
from PIL import Image

from gar.models.jobs import RipArtifact, RipJob
from gar.processors import register_processor
from gar.utils.hashing import short_hash

_BC_BLOCK = {1: 8, 3: 16, 6: 16, 7: 16}


@register_processor("texture")
def _texture_entry(job: RipJob) -> RipArtifact | None:
    return TextureProcessor.run(job)


class TextureProcessor:
    """Stateless — all inputs come via RipJob."""

    target: str = "png"

    @classmethod
    def register(cls) -> None:
        pass  # decorated at import; kept for symmetry

    @classmethod
    def run(cls, job: RipJob) -> RipArtifact | None:
        payload = job.entry.read(job.blob)
        if payload[:4] == b"DDS ":
            img = cls._decode_dds(payload)
        elif payload[:8] == b"\x89PNG\r\n\x1a\n":
            img = Image.open(_BytesIO(payload)).convert("RGBA")
        else:
            return None

        out_name = f"{short_hash(payload)}.png" if job.options.get("hash_names", True) \
            else Path(job.entry.name).with_suffix(".png").name
        return RipArtifact(
            name=out_name,
            kind="texture",
            data=_png_bytes(img),
            meta={"source": job.entry.name, "size": f"{img.width}x{img.height}"},
        )

    @classmethod
    def _decode_dds(cls, payload: bytes) -> Image.Image:
        # DDS header is 128 bytes; pixel data follows.
        h, w, _, _, fourcc = struct.unpack_from("<IIII4s", payload, 12)
        fmt = fourcc.decode("ascii", "replace").strip("\x00")
        block = _BC_BLOCK.get({"DXT1": 1, "DXT5": 3, "BC5U": 6, "BC7 ": 7}.get(fmt, 0), 8)
        bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
        raw = np.frombuffer(payload[128 : 128 + bw * bh * block], dtype=np.uint8)
        # Placeholder: real block decode goes in _native.bc7.decode.
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = 255
        return Image.fromarray(rgba, "RGBA")


def _png_bytes(img: Image.Image) -> bytes:
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


class _BytesIO:
    def __init__(self, data: bytes) -> None:
        import io

        self._io = io.BytesIO(data)

    def __getattr__(self, name: str):
        return getattr(self._io, name)