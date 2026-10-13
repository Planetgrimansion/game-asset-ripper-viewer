"""Processor registry and dispatcher.

Processors are registered by `kind`. The dispatcher picks the first one
whose `accepts(kind)` returns True, in registration order.
"""

from __future__ import annotations

from collections.abc import Callable

from gar.models.jobs import RipArtifact, RipJob
from gar.processors.audio import AudioProcessor
from gar.processors.meshes import MeshProcessor
from gar.processors.textures import TextureProcessor

Processor = Callable[[RipJob], RipArtifact]

_REGISTRY: dict[str, Processor] = {}


def register_processor(*kinds: str) -> Callable[[Processor], Processor]:
    def deco(fn: Processor) -> Processor:
        for k in kinds:
            _REGISTRY[k] = fn
        return fn

    return deco


def dispatch(job: RipJob) -> RipArtifact | None:
    """Route a job to the processor registered for its kind."""
    fn = _REGISTRY.get(job.entry.kind)
    if fn is None:
        return None
    return fn(job)


# Register the built-ins.
TextureProcessor.register()
MeshProcessor.register()
AudioProcessor.register()