from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from typing import Any, Optional

from .constants import (
    ApiField,
    CollectionDefaults,
    DefaultName,
    Encoding,
    Defaults,
    Endpoint,
    JsonKey,
    MarkdownText,
    Newline,
    SanitizeDefaults,
    TableInternal,
    Text,
)
from .env import JsonUnwrapper
from .errors import ApiError, CliError
from .http_client import HttpClient
from .models import AppSummary


class TabidooApi:
    def __init__(self, client: HttpClient) -> None:
        self._client = client

    def get_user(self) -> dict[str, Any]:
        payload = self._client.get_json(Endpoint.USERS_ME)
        data = JsonUnwrapper.unwrap(payload)
        if isinstance(data, dict):
            return data
        return {JsonKey.DATA: data}

    def list_apps(self) -> list[AppSummary]:
        payload = self._client.get_json(Endpoint.APPS)
        data = JsonUnwrapper.unwrap(payload)
        if not isinstance(data, list):
            raise ApiError(Text.APPS_SHAPE)
        return [AppSummary.from_payload(a) for a in data if isinstance(a, dict)]

    def get_app_full(self, app_id: str) -> dict[str, Any]:
        payload = self._client.get_json(Endpoint.APP_DETAIL.format(app_id=app_id))
        data = JsonUnwrapper.unwrap(payload)
        if not isinstance(data, dict):
            raise ApiError(Text.APP_SHAPE)
        return data

    def get_table_data(self, app_id: str, table_internal: TableInternal) -> Optional[list[dict[str, Any]]]:
        base_path = Endpoint.TABLE_DATA.format(app_id=app_id, table=table_internal)
        limit = Defaults.TABLE_DATA_PAGE_LIMIT
        skip = 0
        records: list[dict[str, Any]] = list(CollectionDefaults.EMPTY)

        while True:
            path = f"{base_path}?limit={limit}&skip={skip}"
            try:
                payload = self._client.get_json(path)
            except CliError:
                return records if records else None

            data = JsonUnwrapper.unwrap(payload)
            if not isinstance(data, list):
                return records if records else None
            if not data:
                break

            page = [row for row in data if isinstance(row, dict)]
            records.extend(page)

            if len(data) < limit:
                break

            skip += len(data)

        return records

    def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
        body: dict[str, Any] = {
            ApiField.APPLICATION_ID: app_id,
            ApiField.ONLY_JS_FUNCTIONS: False,
        }
        if schema_id:
            body[ApiField.SCHEMA_ID] = schema_id

        payload = self._client.post_json(Endpoint.TSD, body)
        if isinstance(payload, dict) and JsonKey.CONTENT in payload and isinstance(payload[JsonKey.CONTENT], str):
            return str(payload[JsonKey.CONTENT])

        unwrapped = JsonUnwrapper.unwrap(payload)
        if isinstance(unwrapped, dict) and JsonKey.CONTENT in unwrapped and isinstance(unwrapped[JsonKey.CONTENT], str):
            return str(unwrapped[JsonKey.CONTENT])

        raise ApiError(Text.TSD_MISSING)


class TsdFetcher:
    def __init__(self, api: TabidooApi, max_in_flight: int = 2) -> None:
        if not 1 <= max_in_flight <= 10:
            raise ValueError("max_in_flight must be between 1 and 10")
        self._api = api
        self._max_in_flight = max_in_flight

    def fetch(self, app_id: str, app_full: dict[str, Any], destination: Path) -> None:
        tables = app_full.get(JsonKey.TABLES)
        if not isinstance(tables, list):
            tables = list(CollectionDefaults.EMPTY)

        parts: list[tuple[str, Path]] = []

        with TemporaryDirectory(prefix="tsd-parts-", dir=destination.parent) as temporary_dir, ThreadPoolExecutor(max_workers=self._max_in_flight) as executor:
            remaining = iter(tables)
            pending: dict[Future[str], int] = {}
            while True:
                while len(pending) < self._max_in_flight:
                    for table in remaining:
                        if not isinstance(table, dict):
                            continue
                        schema_id = str(table.get(JsonKey.ID, SanitizeDefaults.EMPTY)).strip()
                        if not schema_id:
                            continue
                        internal = (
                            str(table.get(JsonKey.INTERNAL_NAME_API, SanitizeDefaults.EMPTY)).strip()
                            or DefaultName.TABLE
                        )
                        parts.append((MarkdownText.TABLE_COMMENT.format(name=internal, schema_id=schema_id), Path(temporary_dir) / str(len(parts))))
                        pending[executor.submit(
                            self._api.get_typescript_definition, app_id=app_id, schema_id=schema_id
                        )] = len(parts) - 1
                        break
                    else:
                        break
                if not pending:
                    break
                completed, unfinished = wait(pending, return_when=FIRST_COMPLETED)
                for future in sorted(completed, key=pending.__getitem__):
                    parts[pending.pop(future)][1].write_bytes(future.result().rstrip().encode(Encoding.UTF8))
                # Release completed futures before refilling either slot; output stays in input order.
                del completed, unfinished, future

            if parts:
                with destination.open("wb") as output:
                    for index, (comment, part) in enumerate(parts):
                        if index:
                            output.write(Newline.DOUBLE.encode(Encoding.UTF8))
                        output.write(comment.encode(Encoding.UTF8))
                        last_content_end = output.tell()
                        output.write(Newline.DOUBLE.encode(Encoding.UTF8))
                        with part.open("rb") as source:
                            copyfileobj(source, output, length=65_536)
                        if part.stat().st_size:
                            last_content_end = output.tell()
                    output.seek(last_content_end)
                    output.truncate()
                    output.write(Newline.LF.encode(Encoding.UTF8))
                return

        destination.write_bytes(self._api.get_typescript_definition(app_id=app_id).encode(Encoding.UTF8))
