# Security Policy

## Scope

`game-asset-ripper-viewer` parses **untrusted binary input** by design.
Every container format we support is a potential memory-safety and
zip-bomb surface. Treat malformed input as hostile.

## Reporting a vulnerability

Open a **private** security advisory on GitHub, or email
`security@game-asset-ripper-viewer.dev` with:

- affected handler/processor/driver and file path
- a minimal reproducer (hex dump or sample blob, ≤64KB if possible)
- observed behavior vs expected
- CVSS-ish severity if you have one

We aim to acknowledge in 72h, patch or mitigate in 14 days for
high-severity issues.

## Known attack surfaces

| Surface | Risk | Mitigation |
|---|---|---|
| `handlers/*` header parsing | integer overflow → huge alloc | `utils/bounds.py` clamps |
| `processors/textures.py` DDS/BCn decode | OOB read on malformed mips | length-checked slices |
| `processors/meshes.py` index buffers | OOB index → segfault in C ext | bounds mask before native call |
| `drivers/sqlite_driver.py` | SQL injection via asset names | parameterized queries only |
| path from container entry | path traversal on extract | `utils/safepath.py` sanitizer |

## Out of scope

- Ripping assets from games you don't own.
- Anti-cheat interaction. This tool is offline; it does not inject.
- Redistribution of ripped content.

## Hardening tips for users

- Run rips in a scratch VM when testing unknown containers.
- Set `GAR_MAX_BLOB_MB` (default 512) to cap single-blob memory.
- Prefer `--driver pack` for untrusted input — it never writes to a
  real path until `finalize()`.