from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .constants import (
    Align,
    ProgressText,
    SpinnerName,
    Style,
    StatsLabel,
    TableHeader,
    Text,
    UiDefaults,
)
from .models import ExportStats
from .errors import UserInputError
from .models import AppSummary


class Ui:
    def __init__(self, console: Console) -> None:
        self._console = console

    @property
    def console(self) -> Console:
        return self._console

    def banner(self) -> None:
        self._console.print(Text.TITLE, style=Style.SUCCESS)

    def info(self, message: str) -> None:
        self._console.print(message, style=Style.INFO)

    def success(self, message: str) -> None:
        self._console.print(message, style=Style.SUCCESS)

    def warning(self, message: str) -> None:
        self._console.print(message, style=Style.WARNING)

    def error(self, message: str) -> None:
        self._console.print(message, style=Style.ERROR)

    def progress(self) -> Progress:
        return Progress(
            SpinnerColumn(style=Style.INFO),
            TextColumn(ProgressText.TASK),
            BarColumn(bar_width=UiDefaults.PROGRESS_BAR_WIDTH),
            TextColumn(ProgressText.FRACTION),
            TimeElapsedColumn(),
            console=self._console,
        )

    def spinner(self, message: str):
        return self._console.status(message, spinner=SpinnerName.DEFAULT)

    def show_stats(self, stats: ExportStats) -> None:
        table = Table(title=Text.STATS_TITLE)
        table.add_column(TableHeader.METRIC)
        table.add_column(TableHeader.VALUE, justify=Align.RIGHT)
        table.add_row(StatsLabel.TABLES, str(stats.tables))
        table.add_row(StatsLabel.FIELDS, str(stats.fields))
        table.add_row(StatsLabel.CODE_BLOCKS, str(stats.code_blocks))
        table.add_row(StatsLabel.WORKFLOWS, str(stats.workflows))
        table.add_row(StatsLabel.CUSTOM_SCRIPTS, str(stats.custom_scripts))
        table.add_row(StatsLabel.SCHEMA_LINES, str(stats.schema_lines))
        table.add_row(StatsLabel.SCHEMA_BYTES, str(stats.schema_bytes))
        table.add_row(StatsLabel.TABLES_MD_LINES, str(stats.tables_md_lines))
        table.add_row(StatsLabel.TABLES_MD_BYTES, str(stats.tables_md_bytes))
        table.add_row(StatsLabel.LLM_LINES, str(stats.llm_lines))
        table.add_row(StatsLabel.LLM_BYTES, str(stats.llm_bytes))
        self._console.print()
        self._console.print(table)


class AppSelector:
    def __init__(self, console: Console) -> None:
        self._console = console

    def select(self, apps: list[AppSummary], app_id: Optional[str], non_interactive: bool) -> AppSummary:
        if app_id:
            for app in apps:
                if app.app_id == app_id:
                    return app
            raise UserInputError(Text.APP_ID_NOT_FOUND.format(app_id=app_id))
        if len(apps) == UiDefaults.INDEX_START:
            return apps[UiDefaults.INDEX_START - UiDefaults.PROGRESS_UNIT]
        if non_interactive:
            raise UserInputError(Text.MULTI_APP_NEED_ID)
        self._print_apps(apps)
        return self._prompt_choice(apps)

    def _print_apps(self, apps: list[AppSummary]) -> None:
        table = Table(title=Text.AVAILABLE_APPS)
        table.add_column(TableHeader.INDEX, justify=Align.RIGHT)
        table.add_column(TableHeader.NAME)
        table.add_column(TableHeader.INTERNAL)
        table.add_column(TableHeader.ID)
        for idx, app in enumerate(apps, start=UiDefaults.INDEX_START):
            table.add_row(str(idx), app.name, app.internal_name, app.app_id)
        self._console.print()
        self._console.print(table)
        self._console.print()

    def _prompt_choice(self, apps: list[AppSummary]) -> AppSummary:
        while True:
            choice = Prompt.ask(Text.SELECT_APP).strip()
            if not choice:
                continue
            for app in apps:
                if app.app_id == choice:
                    return app
            if choice.isdigit():
                idx = int(choice)
                if UiDefaults.INDEX_START <= idx <= len(apps):
                    return apps[idx - UiDefaults.INDEX_START]
            self._console.print(Text.INVALID_SELECTION, style=Style.WARNING)
