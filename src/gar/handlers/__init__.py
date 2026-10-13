"""Container handler registry.

Handlers are matched against a blob by their `signatures` (magic bytes)
and, if needed, a deeper `sniff`. Higher `priority` wins ties.
"""

from __future__ import annotations

from gar.handlers.base import IngestHandler
from gar.handlers.bundles_handler import BundlesHandler
from gar.handlers.paks_handler import PaksHandler
from gar.utils.blob import BlobReader

HANDLERS: tuple[type[IngestHandler], ...] = (
    PaksHandler,
    BundlesHandler,
)


def pick_handler(blob: BlobReader) -> IngestHandler | None:
    """Return the highest-priority handler whose sniff() accepts the blob."""
    candidates = [h for h in HANDLERS if h.sniff(blob)]
    if not candidates:
        return None
    return max(candidates, key=lambda h: h.priority)()