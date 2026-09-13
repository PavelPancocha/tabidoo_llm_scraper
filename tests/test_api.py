from __future__ import annotations

import unittest
from concurrent.futures import Future, wait
from collections.abc import Iterable
from threading import Barrier, Event, Lock
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from unittest.mock import patch

from tabidoo_llm_export.api import TsdFetcher
from tabidoo_llm_export.errors import ApiError


class FakeDefinitionApi:
    def __init__(self, definitions: dict[Optional[str], str]) -> None:
        self.definitions = definitions
        self.calls: list[tuple[str, Optional[str]]] = []

    def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
        self.calls.append((app_id, schema_id))
        return self.definitions[schema_id]


def fetch_text(fetcher: TsdFetcher, app_full: dict[str, object]) -> str:
    with TemporaryDirectory() as directory:
        destination = Path(directory) / "schema.ts"
        fetcher.fetch("app-1", app_full, destination)
        return destination.read_bytes().decode("utf-8")


class TsdFetcherTests(unittest.TestCase):
    def test_bounded_pairs_preserve_order_and_propagate_failure_without_retry(self) -> None:
        class ConcurrentApi(FakeDefinitionApi):
            def __init__(self, fail: bool) -> None:
                super().__init__({str(i): f"definition-{i}\n" for i in range(4)})
                self.fail = fail
                self.barrier = Barrier(2, timeout=2)
                self.completed_second = [Event(), Event()]
                self.lock = Lock()
                self.active = 0
                self.maximum = 0
                self.finished: list[str] = []

            def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
                assert schema_id is not None
                index = int(schema_id)
                with self.lock:
                    self.calls.append((app_id, schema_id))
                    self.active += 1
                    self.maximum = max(self.maximum, self.active)
                try:
                    self.barrier.wait()
                    if index % 2 == 0:
                        assert self.completed_second[index // 2].wait(2)
                    if self.fail and index == 1:
                        raise ApiError("definition failed")
                    return self.definitions[schema_id]
                finally:
                    with self.lock:
                        self.finished.append(schema_id)
                        self.active -= 1
                    if index % 2 == 1 and not self.fail:
                        self.completed_second[index // 2].set()

        for fail in (False, True):
            with self.subTest(fail=fail):
                api = ConcurrentApi(fail)
                tables = [{"id": str(i), "internalNameApi": f"table-{i}"} for i in range(4)]
                fetcher = TsdFetcher(api)  # type: ignore[arg-type]
                if fail:
                    def release_after_failure(futures: Iterable[Future[str]], *, return_when: str) -> tuple[set[Future[str]], set[Future[str]]]:
                        pending = list(futures)
                        # The peer can finish only after the failing Future is observably done.
                        pending[1].add_done_callback(lambda completed: api.completed_second[0].set())
                        return wait(pending, return_when=return_when)

                    with patch("tabidoo_llm_export.api.wait", side_effect=release_after_failure), self.assertRaisesRegex(ApiError, "definition failed"):
                        fetch_text(fetcher, {"tables": tables})
                else:
                    result = fetch_text(fetcher, {"tables": tables})
                    self.assertEqual(result, "\n\n".join(
                        f"// Table: table-{i} ({i})\n\ndefinition-{i}" for i in range(4)
                    ) + "\n")
                self.assertEqual(api.maximum, 2)
                self.assertEqual(api.active, 0)
                self.assertEqual(api.finished, ["1", "0"] if fail else ["1", "0", "3", "2"])
                self.assertCountEqual(api.calls, [("app-1", str(i)) for i in range(2 if fail else 4)])

    def test_refills_either_completed_slot_while_other_request_is_pending(self) -> None:
        for slow_index in (0, 1):
            with self.subTest(slow_index=slow_index):
                class RollingApi(FakeDefinitionApi):
                    def __init__(self) -> None:
                        super().__init__({str(i): f"definition-{i}\n" for i in range(4)})
                        self.slow_started = Event()
                        self.refilled = Event()
                        self.lock = Lock()
                        self.active: set[int] = set()
                        self.maximum = 0

                    def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
                        assert schema_id is not None
                        index = int(schema_id)
                        with self.lock:
                            self.calls.append((app_id, schema_id))
                            self.active.add(index)
                            self.maximum = max(self.maximum, len(self.active))
                        try:
                            if index == slow_index:
                                self.slow_started.set()
                                assert self.refilled.wait(2), "Pair barrier left a completed slot idle"
                            elif index < 2:
                                assert self.slow_started.wait(2)
                            elif index == 2:
                                with self.lock:
                                    assert slow_index in self.active
                                self.refilled.set()
                            return self.definitions[schema_id]
                        finally:
                            with self.lock:
                                self.active.remove(index)

                api = RollingApi()
                tables = [{"id": str(i), "internalNameApi": f"table-{i}"} for i in range(4)]
                result = fetch_text(TsdFetcher(api), {"tables": tables})  # type: ignore[arg-type]
                self.assertEqual(result, "\n\n".join(
                    f"// Table: table-{i} ({i})\n\ndefinition-{i}" for i in range(4)
                ) + "\n")
                self.assertCountEqual(api.calls, [("app-1", str(i)) for i in range(4)])
                self.assertEqual(api.maximum, 2)
                self.assertFalse(api.active)

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

        result = fetch_text(TsdFetcher(api), app_full)  # type: ignore[arg-type]

        self.assertCountEqual(api.calls, [("app-1", "table-1"), ("app-1", "table-2")])
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

        result = fetch_text(TsdFetcher(api), app_full)  # type: ignore[arg-type]

        self.assertEqual(api.calls, [("app-1", "table-1")])
        self.assertIn("// Table: table (table-1)", result)

    def test_falls_back_to_app_level_schema_when_no_valid_table_ids_exist(self) -> None:
        api = FakeDefinitionApi({None: "export interface IDooModelBase {}"})
        app_full = {"tables": [{"internalNameApi": "missing_id"}]}

        result = fetch_text(TsdFetcher(api), app_full)  # type: ignore[arg-type]

        self.assertEqual(api.calls, [("app-1", None)])
        self.assertEqual(result, "export interface IDooModelBase {}")


if __name__ == "__main__":
    unittest.main()
