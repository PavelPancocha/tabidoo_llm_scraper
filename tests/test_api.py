from __future__ import annotations

import unittest
from typing import Optional

from tabidoo_llm_export.api import TsdFetcher


class FakeDefinitionApi:
    def __init__(self, definitions: dict[Optional[str], str]) -> None:
        self.definitions = definitions
        self.calls: list[tuple[str, Optional[str]]] = []

    def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
        self.calls.append((app_id, schema_id))
        return self.definitions[schema_id]


class TsdFetcherTests(unittest.TestCase):
    def test_fetches_and_concatenates_schema_definitions_per_table(self) -> None:
        api = FakeDefinitionApi(
            {
                "table-1": "export interface IDooApiTableOrders {}\n",
                "table-2": "export interface IDooApiTableInvoices {}\n",
            }
        )
        app_full = {
            "tables": [
                {"id": "table-1", "internalNameApi": "orders"},
                {"id": "table-2", "internalNameApi": "invoices"},
            ]
        }

        result = TsdFetcher(api).fetch("app-1", app_full)  # type: ignore[arg-type]

        self.assertEqual(api.calls, [("app-1", "table-1"), ("app-1", "table-2")])
        self.assertEqual(
            result,
            "// Table: orders (table-1)\n\n"
            "export interface IDooApiTableOrders {}\n\n"
            "// Table: invoices (table-2)\n\n"
            "export interface IDooApiTableInvoices {}\n",
        )

    def test_skips_malformed_tables_and_uses_default_table_name(self) -> None:
        api = FakeDefinitionApi({"table-1": "export interface IDooApiTableUnknown {}"})
        app_full = {
            "tables": [
                None,
                {"internalNameApi": "missing_id"},
                {"id": "table-1", "internalNameApi": ""},
            ]
        }

        result = TsdFetcher(api).fetch("app-1", app_full)  # type: ignore[arg-type]

        self.assertEqual(api.calls, [("app-1", "table-1")])
        self.assertIn("// Table: table (table-1)", result)

    def test_falls_back_to_app_level_schema_when_no_valid_table_ids_exist(self) -> None:
        api = FakeDefinitionApi({None: "export interface IDooModelBase {}"})
        app_full = {"tables": [{"internalNameApi": "missing_id"}]}

        result = TsdFetcher(api).fetch("app-1", app_full)  # type: ignore[arg-type]

        self.assertEqual(api.calls, [("app-1", None)])
        self.assertEqual(result, "export interface IDooModelBase {}")


if __name__ == "__main__":
    unittest.main()
