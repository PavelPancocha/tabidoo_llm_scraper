from __future__ import annotations

from typing import Any, Optional

from .constants import (
    ApiField,
    CollectionDefaults,
    Defaults,
    Endpoint,
    JsonKey,
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
    def __init__(self, api: TabidooApi) -> None:
        self._api = api

    def fetch(self, app_id: str) -> str:
        return self._api.get_typescript_definition(app_id=app_id)
