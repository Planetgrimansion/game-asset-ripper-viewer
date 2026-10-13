# Contributing to game-asset-ripper-viewer

This repo is a community-driven **game asset ripper / viewer** — it walks
game data containers (paks, bundles, archives, loose files), identifies
asset payloads, converts them into viewable/interchangeable formats, and
exports them with a manifest. It is a pipeline: **ingest → process →
export**, wired through a job queue.

We treat this like any other modding/exploit-research codebase: real
vocabulary, real containers, real formats. No sanitizing.

## Ground rules

1. **One handler, one container family.** If `PaksHandler` starts sprouting
   Unity bundle logic, that logic belongs in `BundlesHandler`.
2. **Processors are pure-ish.** A processor takes a `RipJob` plus a
   `BlobRef`, returns a `RipArtifact` or raises. No global state, no
   writing to disk. Output drivers do the disk writes.
3. **Output drivers are the only thing that touches the filesystem.**
   `FsDriver`, `PackDriver`, `SQLiteDriver` — pick one per run.
4. **Every new format gets a fixture.** Drop a tiny sample into
   `tests/fixtures/` and register it. If it's >2MB, add it to `.gitignore`
   and document the download URL in the test docstring.
5. **No magic numbers in handlers.** Header signatures, block sizes and
   offsets live in `src/gar/models/signatures.py`.

## Adding a container handler

1. Subclass `IngestHandler` in `src/gar/handlers/`.
2. Declare `signatures: tuple[bytes, ...]` and `priority: int`.
3. Implement `sniff(blob) -> bool` and `iter_entries(blob) -> Iterator[Entry]`.
4. Register it in `src/gar/handlers/__init__.py::HANDLERS`.
5. Add a fixture + a test in `tests/test_handlers.py`.

## Adding a processor

Processors live in `src/gar/processors/`. Register via the
`@register_processor("texture")` decorator. The dispatcher picks processors
by the `kind` field produced by the handler.

## Adding an output driver

Drivers live in `src/gar/drivers/`. Implement `OutputDriver.write(artifact)`
and `OutputDriver.finalize()`. Drivers must be safe to call from multiple
worker threads — use the provided `DriverLock` if you need serialization.

## Dev loop

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows
pip install -e ".[dev]"
pytest -q
ruff check src tests
mypy src
```

## Commit style

`handlers: add UE5 .utoc/.ucas sniff`
`processors: fix DDS mip-chain offset for BC7`
`drivers: fs — hash-named subdir sharding`

## Legal

This tool exists for **modding, preservation, and personal research on
software you own**. Do not redistribute ripped assets you don't have
rights to. That's on you, not on the repo.