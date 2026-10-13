"""Mesh processor: PSK / FBX / custom binary -> OBJ or glTF.

We don't reimplement a full FBX SDK; instead we read the vertex/index
buffers directly when the container gives us offsets, and fall back to
assimp-style loaders via subprocess for the rest.
"""

from __future__ import annotations

import struct

import numpy as np

from gar.models.jobs import RipArtifact, RipJob
from gar.processors import register_processor
from gar.utils.hashing import short_hash


@register_processor("mesh")
def _mesh_entry(job: RipJob) -> RipArtifact | None:
    payload = job.entry.read(job.blob)
    verts, faces = MeshProcessor.parse(payload