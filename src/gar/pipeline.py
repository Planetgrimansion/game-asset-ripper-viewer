"""Pipeline driver: ingest -> process -> export, worker-pool style.

The pipeline is deliberately dumb: it knows about *handlers*, *processors*
and *drivers* only through their registries. Adding a new format is a
new module + a decorator, not a change here.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from gar.config.settings import Settings
from gar.drivers import make_driver
from gar.drivers.base import OutputDriver
from gar.handlers import pick_handler
from gar.models.entries import Entry
from gar.models.jobs import RipArtifact, RipJob
from gar.processors import dispatch
from gar.utils.blob import BlobReader
from gar.utils.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class RipRequest:
    container: Path
    settings: Settings


@dataclass(slots=True)
class RipReport:
    total: int = 0
    written: int = 0
    skipped: int = 0
    failed: int = 0
    elapsed_s: float = 0.0
    errors: list[tuple[str, str]] = field(default_factory=list)


def rip(req: RipRequest) -> RipReport:
    """Run the full pipeline over a container. Blocking; safe to call once."""
    t0 = time.perf_counter()
    report = RipReport()
    blob = BlobReader.from_file(req.container)

    handler = pick_handler(blob)
    if handler is None:
        raise RuntimeError(f"no handler for {req.container.name}")

    driver: OutputDriver = make_driver(req.settings)
    entries: list[Entry] = list(handler.iter_entries(blob))
    report.total = len(entries)

    with ThreadPoolExecutor(max_workers=req.settings.workers) as pool:
        futures = {
            pool.submit(_process_one, e, blob, req.settings): e
            for e in entries
        }
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                artifact = fut.result()
            except Exception as exc:  # noqa: BLE001 — pipeline boundary
                log.warning("failed %s: %s", entry.name, exc)
                report.failed += 1
                report.errors.append((entry.name, str(exc)))
                continue
            if artifact is None:
                report.skipped += 1
                continue
            driver.write(artifact)
            report.written += 1

    driver.finalize()
    report.elapsed_s = time.perf_counter() - t0
    log.info(
        "rip done: %d/%d written, %d failed in %.2fs",
        report.written, report.total, report.failed, report.elapsed_s,
    )
    return report


def _process_one(entry: Entry, blob: BlobReader, settings: Settings) -> RipArtifact | None:
    if settings.kinds and entry.kind not in settings.kinds:
        return None
    job = RipJob(
        entry=entry,
        blob=blob,
        out_dir=settings.out_dir,
        options=settings.processor_options,
    )
    return dispatch(job)