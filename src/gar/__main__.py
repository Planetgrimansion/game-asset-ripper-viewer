"""Allow `python -m gar` — thin shim to the CLI."""

from gar.cli import main

if __name__ == "__main__":
    raise SystemExit(main())