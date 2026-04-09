from __future__ import annotations

from pathlib import Path
from typing import Optional

from .api import TabidooApi, TsdFetcher
from .constants import (
    CollectionDefaults,
    JsonKey,
    Prefix,
    ProgressStep,
    TableInternal,
    Text,
)
from .errors import ApiError, CliError, UserInputError
from .extractor import ScriptExtractor
from .formatters import LlmFormatter, TablesFormatter
from .http_client import HttpClient
from .output import OutputWriter
from .stats import StatsBuilder
from .ui import AppSelector, Ui


class ExportRunner:
    def __init__(
        self,
        ui: Ui,
        base_url: str,
        token: str,
        language: str,
        timeout_sec: int,
        verbose: bool,
    ) -> None:
        self._ui = ui
        self._base_url = base_url
        self._token = token
        self._language = language
        self._timeout_sec = timeout_sec
        self._verbose = verbose

    def run(self, app_id: Optional[str], out_dir: Path, non_interactive: bool) -> tuple[Path | None, Path, Path]:
        client = HttpClient(
            self._base_url,
            self._token,
            self._language,
            self._timeout_sec,
            self._verbose,
            self._ui.console,
        )
        api = TabidooApi(client)
        selector = AppSelector(self._ui.console)
        extractor = ScriptExtractor()
        formatter = LlmFormatter()
        tables_formatter = TablesFormatter()
        writer = OutputWriter()
        tsd_fetcher = TsdFetcher(api)

        with self._ui.spinner(Text.AUTHENTICATING) as status:
            user = api.get_user()
            status.update(Text.LOADING_APPS)
            apps = api.list_apps()

        self._ui.info(Text.USING_INSTANCE.format(base_url=self._base_url))
        user_email = user.get(JsonKey.EMAIL)
        if user_email:
            self._ui.info(Text.AUTHENTICATED_AS.format(email=user_email))

        if not apps:
            raise UserInputError(Text.NO_APPS)

        selected = selector.select(apps, app_id, non_interactive)
        if not selected.app_id:
            raise ApiError(Text.MISSING_APP_ID)

        with self._ui.spinner(Text.LOADING_APP) as status:
            app_full = api.get_app_full(selected.app_id)

        with self._ui.progress() as progress:
            export_task = progress.add_task(Text.EXPORTING, total=len(ProgressStep))

            progress.update(export_task, description=Text.FETCHING_TSD)
            schema_md: str | None = None
            try:
                schema_md = tsd_fetcher.fetch(selected.app_id)
            except CliError as exc:
                self._ui.warning(Text.SKIP_SCHEMA_ERROR.format(reason=str(exc)))
            progress.advance(export_task)

            progress.update(export_task, description=Text.BUILDING_TABLES)
            tables_md = tables_formatter.format(app_full)
            progress.advance(export_task)

            progress.update(export_task, description=Text.FETCHING_WORKFLOWS)
            workflows_table = api.get_table_data(selected.app_id, TableInternal.WORKFLOWS)
            progress.advance(export_task)

            progress.update(export_task, description=Text.FETCHING_CUSTOM)
            custom_scripts_table = api.get_table_data(selected.app_id, TableInternal.CUSTOM_SCRIPTS)
            progress.advance(export_task)

            progress.update(export_task, description=Text.EXTRACTING)
            extracted = extractor.extract(app_full)
            workflows = (
                extractor.extract_workflows(workflows_table)
                if workflows_table
                else list(CollectionDefaults.EMPTY)
            )
            custom_scripts = (
                extractor.extract_custom_scripts(custom_scripts_table)
                if custom_scripts_table
                else list(CollectionDefaults.EMPTY)
            )
            llm_md = formatter.format(extracted, workflows, custom_scripts)
            progress.advance(export_task)

            progress.update(export_task, description=Text.WRITING)
            schema_path, tables_path, scripts_path = writer.write(
                out_dir,
                selected,
                schema_md,
                tables_md,
                llm_md,
            )
            progress.advance(export_task)

        stats = StatsBuilder.build(
            app_full,
            extracted,
            workflows,
            custom_scripts,
            schema_md or "",
            tables_md,
            llm_md,
        )
        self._ui.show_stats(stats)
        self._ui.success(Text.DONE)
        self._ui.info(Text.WROTE)
        if schema_path is not None:
            self._ui.info(f"{Prefix.BULLET}{schema_path}")
        self._ui.info(f"{Prefix.BULLET}{tables_path}")
        self._ui.info(f"{Prefix.BULLET}{scripts_path}")
        return schema_path, tables_path, scripts_path
