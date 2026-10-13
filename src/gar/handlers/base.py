"""Base class for ingest handlers.

A handler is responsible for *reading* a container: it decides whether a
blob is its format, and it yields `Entry` records describing every asset
inside. Handlers never write to disk and never decode payloads — that's
the processor's job.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from gar.models.entries import Entry
from gar.utils.blob import BlobReader


class IngestHandler(ABC):
    name: str = "base"
    priority: int = 0
    signatures: tuple[bytes, ...] = ()

    @classmethod
    def sniff(cls, blob: BlobReader) -> bool:
        """Cheap check: does the blob look like our format?"""
        if not cls.signatures:
            return False
        head = blob.peek(16)
        return any(head.startswith(sig) for sig in cls.signatures)

    @abstractmethod
    def iter_entries(self, blob: BlobReader) -> Iterator[Entry]:
        """Yield one Entry per asset found in the container."""

    def describe(self, blob: BlobReader) -> str:
        """Short human-readable summary, used by `gar info`."""
        return f"{self.name} container, {blob.size} bytes"