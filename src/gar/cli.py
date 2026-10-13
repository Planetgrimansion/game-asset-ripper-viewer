"""Command-line entry point for the ripper/viewer.

Usage:
    gar scan   <container>              # list entries, no extraction
    gar rip    <container> -o out/      # full rip
    gar view   <asset.rip>              # open a rippack in the TUI viewer
    gar info   <container>              # sniff handler + summary
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from gar.config.settings import load_settings
from gar.pipeline import RipRequest, rip
from gar.utils.logging import configure_logging

console = Console()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", "-v", is_flag=True, help="Debug logging.")
@click.version_option(package_name="game-asset-ripper-viewer")
def main(verbose: bool) -> None:
    """Game asset ripper / viewer."""
    configure_logging(level="DEBUG" if verbose else "INFO")


@main.command()
@click.argument("container", type=click.Path(exists=True, path_type=Path))
def info(container: Path) -> None:
    """Sniff the container and print a summary."""
    from gar.handlers import pick_handler
    from gar.utils.blob import BlobReader

    blob = BlobReader.from_file(container)
    handler = pick_handler(blob)
    if handler is None:
        console.print(f"[red]no handler[/red] for {container.name}")
        sys.exit(2)
    console.print(f"[green]{handler.name}[/green] :: {handler.describe(blob)}")


@main.command()
@click.argument("container", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("out"))
@click.option("--driver", type=click.Choice(["fs", "pack", "sqlite"]), default="fs")
@click.option("--kinds", "-k", multiple=True, help="Only rip these kinds (texture, mesh, audio).")
@click.option("--workers", "-j", type=int, default=0, help="0 = auto (cpu_count).")
def rip_cmd(container: Path, out: Path, driver: str, kinds: tuple[str, ...], workers: int) -> None:
    """Rip a container to an output directory."""
    settings = load_settings()
    settings.driver = driver
    settings.out_dir = out
    settings.kinds = set(kinds) if kinds else None
    settings.workers = workers or settings.workers

    report = rip(RipRequest(container=container, settings=settings))
    console.print(
        f"[bold]{report.total}[/bold] assets, "
        f"[green]{report.written}[/green] written, "
        f"[yellow]{report.skipped}[/yellow] skipped, "
        f"[red]{report.failed}[/red] failed "
        f"in {report.elapsed_s:.2f}s"
    )
    if report.failed:
        sys.exit(1)


main.add_command(rip_cmd, name="rip")

if __name__ == "__main__":
    raise SystemExit(main())