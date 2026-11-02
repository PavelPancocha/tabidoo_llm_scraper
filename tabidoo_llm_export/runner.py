from __future__ import annotations

import json
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from .api import TabidooApi, TsdFetcher
from .constants import (
    CollectionDefaults,
    Defaults,
    EnvVar,
    JsonKey,
    Prefix,
    ProgressStep,
    TableInternal,
    Text,
)
from .errors import ApiError, InvalidConfigError, UserInputError
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
        tsd_fetcher = TsdFetcher(api, tsd_max_in_flight())

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

        with TemporaryDirectory(prefix="tabidoo-schema-") as temporary_dir, self._ui.progress() as progress:
            export_task = progress.add_task(Text.EXPORTING, total=len(ProgressStep))

            progress.update(export_task, description=Text.FETCHING_TSD)
            schema_md = Path(temporary_dir) / "schema.ts"
            tsd_fetcher.fetch(selected.app_id, app_full, schema_md)
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

            progress.update(export_task, description=Text.FETCHING_WIDGETS)
            widgets_table = api.get_table_data(selected.app_id, TableInternal.WIDGETS)
            progress.advance(export_task)

            for table, rows in ((TableInternal.WORKFLOWS, workflows_table), (TableInternal.CUSTOM_SCRIPTS, custom_scripts_table), (TableInternal.WIDGETS, widgets_table)):
                counts = api.system_table_counts.get(str(table))
                if counts != {"expected": len(rows), "fetched": len(rows)}:
                    raise ApiError(f"Incomplete system-table count for {table}")

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
            widgets = (
                extractor.extract_widgets(widgets_table)
                if widgets_table
                else list(CollectionDefaults.EMPTY)
            )
            llm_md = formatter.format(extracted, workflows, custom_scripts, widgets)
            expected_fragments = {"tableScripts": len(extracted.fragments), "workflows": len(workflows), "customScripts": len(custom_scripts), "widgets": len(widgets)}
            progress.advance(export_task)

            progress.update(export_task, description=Text.WRITING)
            schema_path, tables_path, scripts_path = writer.write(
                out_dir,
                selected,
                schema_md,
                tables_md,
                llm_md,
            )
            table_count = len(app_full[JsonKey.TABLES])
            if schema_path is None:
                raise ApiError("Missing written schema")
            written_scripts = scripts_path.read_text(encoding="utf-8")
            for key, heading in (("tableScripts", "## Code Block "), ("workflows", "### Workflow "), ("customScripts", "### Custom Script "), ("widgets", "### Widget ")):
                if len(re.findall(r"^" + re.escape(heading), written_scripts, re.MULTILINE)) != expected_fragments[key]:
                    raise ApiError("Incomplete written script section: " + key)
            with schema_path.open(encoding="utf-8") as written_schema:
                if sum(line.startswith("// Table: ") for line in written_schema) != table_count:
                    raise ApiError("Incomplete written schema section")
            completeness = {
                "version": 1,
                "status": "PASS",
                "appId": selected.app_id,
                "tables": {"expected": table_count, "tsdFetched": table_count},
                "systemTables": api.system_table_counts,
                "fragments": expected_fragments,
            }
            (out_dir / "export-completeness.json").write_text(json.dumps(completeness, indent=2) + "\n", encoding="utf-8")
            progress.advance(export_task)

            stats = StatsBuilder.build(
                app_full,
                extracted,
                workflows,
                custom_scripts,
                schema_md,
                tables_md,
                llm_md,
                widgets,
            )
        self._ui.show_stats(stats)
        self._ui.success(Text.DONE)
        self._ui.info(Text.WROTE)
        if schema_path is not None:
            self._ui.info(f"{Prefix.BULLET}{schema_path}")
        self._ui.info(f"{Prefix.BULLET}{tables_path}")
        self._ui.info(f"{Prefix.BULLET}{scripts_path}")
        return schema_path, tables_path, scripts_path


def tsd_max_in_flight() -> int:
    raw = os.environ.get(EnvVar.TSD_CONCURRENCY, "").strip()
    if not raw:
        return Defaults.TSD_MAX_IN_FLIGHT
    if not raw.isdigit() or not 1 <= int(raw) <= 10:
        raise InvalidConfigError(f"{EnvVar.TSD_CONCURRENCY} must be an integer between 1 and 10")
    return int(raw)
