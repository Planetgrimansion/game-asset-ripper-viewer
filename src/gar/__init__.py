"""game-asset-ripper-viewer — pipeline core.

Public surface:

    from gar import rip, RipRequest, RipReport

The pipeline is: IngestHandler -> Processor -> OutputDriver, driven
by a worker pool in gar.pipeline.
"""

from gar.pipeline import RipReport, RipRequest, rip

__all__ = ["rip", "RipRequest", "RipReport"]
__version__ = "0.9.3"