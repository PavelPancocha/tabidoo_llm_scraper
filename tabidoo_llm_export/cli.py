from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .constants import CliOption, Defaults, EntryPoint, EnvDefaults, ExitCode, HelpText, Text
from .env import EnvLoader, TokenProvider, UrlNormalizer
from .errors import CliError
from .runner import ExportRunner
from .ui import Ui

app = typer.Typer(add_help_option=True)


@app.command()
def export(
    app_id: Optional[str] = typer.Option(None, *CliOption.APP_ID, help=HelpText.APP_ID),
    out_dir: Path = typer.Option(Path(Defaults.OUT_DIR), *CliOption.OUT_DIR, help=HelpText.OUT_DIR),
    base_url: str = typer.Option(Defaults.BASE_URL, *CliOption.BASE_URL, help=HelpText.BASE_URL),
    language: str = typer.Option(Defaults.LANGUAGE, *CliOption.LANGUAGE, help=HelpText.LANGUAGE),
    no_interactive: bool = typer.Option(False, *CliOption.NO_INTERACTIVE, help=HelpText.NO_INTERACTIVE),
    timeout: int = typer.Option(Defaults.TIMEOUT_SEC, *CliOption.TIMEOUT, help=HelpText.TIMEOUT),
    verbose: bool = typer.Option(False, *CliOption.VERBOSE, help=HelpText.VERBOSE),
) -> None:
    console = Console()
    ui = Ui(console)
    ui.banner()

    EnvLoader.load(Path.cwd() / EnvDefaults.DOTENV)

    token = TokenProvider.read()
    normalized_url = UrlNormalizer.normalize(base_url)

    runner = ExportRunner(
        ui=ui,
        base_url=normalized_url,
        token=token,
        language=language,
        timeout_sec=timeout,
        verbose=verbose,
    )

    try:
        runner.run(app_id=app_id, out_dir=out_dir.expanduser().resolve(), non_interactive=no_interactive)
    except CliError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=int(exc.exit_code))
    except KeyboardInterrupt:
        ui.error(Text.CANCELLED)
        raise typer.Exit(code=int(ExitCode.CANCELLED))


def main() -> None:
    app()


if __name__ == EntryPoint.MAIN:
    main()
