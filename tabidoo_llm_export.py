#!/usr/bin/env python3
"""
Tabidoo LLM Export CLI (standalone, single-file).

Flow:
1) Put .env next to this script with TABIDOO_API_KEY=...
2) Run the script
3) Validate token and list apps
4) Select app (or auto-continue if only one / --app-id)
5) Export:
   - TypeScript definitions (.d.ts)
   - LLM scripts markdown (from app schema, workflows, custom scripts)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://app.tabidoo.cloud"
DEFAULT_TIMEOUT_SEC = 30


# -------------------------
# Errors / exit codes
# -------------------------

class CliError(Exception):
    exit_code: int = 1


class InvalidConfigError(CliError):
    exit_code = 2


class AuthError(CliError):
    exit_code = 3


class NetworkError(CliError):
    exit_code = 4


class ApiError(CliError):
    exit_code = 5


class UserInputError(CliError):
    exit_code = 6


class HttpStatusError(ApiError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


# -------------------------
# Utilities
# -------------------------

def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def sanitize_for_fs(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9_\-\.]+", "", value)
    value = value.strip("._-")
    return value or "app"


def load_dotenv(dotenv_path: Path) -> None:
    """
    Minimal .env loader:
    - KEY=VALUE
    - ignores comments and empty lines
    - supports quoted values
    - does not override existing process env
    """
    if not dotenv_path.exists():
        return

    raw = dotenv_path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and ((value[0] == value[-1]) and value[0] in ("'", '"')):
            value = value[1:-1]

        if key and key not in os.environ:
            os.environ[key] = value


def unwrap_tabidoo_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def json_dumps_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=False)


def build_appinfo_header(app_id: str, language: str = "en") -> str:
    app_info = {
        "appId": app_id,
        "language": language,
        "customData": {},
        "browserLanguage": "",
    }
    return quote(json_dumps_compact(app_info), safe="")


def normalize_base_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise InvalidConfigError("Base URL is empty.")
    if not value.startswith("http://") and not value.startswith("https://"):
        raise InvalidConfigError("Base URL must start with http:// or https://")
    return value.rstrip("/")


# -------------------------
# HTTP client
# -------------------------

@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


def http_request(
    *,
    base_url: str,
    path: str,
    method: str,
    token: str,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    verbose: bool = False,
) -> HttpResponse:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json_body is not None:
        req_headers["Content-Type"] = "application/json"

    if headers:
        req_headers.update(headers)

    data: Optional[bytes] = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=True).encode("utf-8")

    if verbose:
        print(f"{method.upper()} {url}")

    request = Request(url=url, method=method.upper(), headers=req_headers, data=data)

    try:
        with urlopen(request, timeout=timeout_sec) as resp:
            body = resp.read()
            return HttpResponse(
                status=getattr(resp, "status", 200),
                headers={k.lower(): v for k, v in resp.headers.items()},
                body=body,
            )
    except HTTPError as exc:
        body = exc.read() if exc.fp else b""
        status = exc.code
        message = format_http_error(status, url, body)
        if status in (401, 403):
            raise AuthError(message) from exc
        raise HttpStatusError(status, message) from exc
    except URLError as exc:
        raise NetworkError(f"Network error calling {url}: {exc}") from exc


def format_http_error(status: int, url: str, body: bytes) -> str:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return f"HTTP {status} calling {url} (empty error body)"
    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and "errors" in payload and isinstance(payload["errors"], list):
            msgs = []
            for item in payload["errors"]:
                if isinstance(item, dict) and "message" in item:
                    msgs.append(str(item["message"]))
            if msgs:
                return f"HTTP {status} calling {url}: " + "; ".join(msgs)
    except Exception:
        pass
    trimmed = textwrap.shorten(text, width=800, placeholder="...")
    return f"HTTP {status} calling {url}: {trimmed}"


def http_get_json(
    *,
    base_url: str,
    path: str,
    token: str,
    headers: dict[str, str] | None = None,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    verbose: bool = False,
) -> Any:
    resp = http_request(
        base_url=base_url,
        path=path,
        method="GET",
        token=token,
        headers=headers,
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    try:
        return json.loads(resp.body.decode("utf-8"))
    except Exception as exc:
        raise ApiError(f"Invalid JSON response from GET {path}") from exc


def http_post_json(
    *,
    base_url: str,
    path: str,
    token: str,
    json_body: Any,
    headers: dict[str, str] | None = None,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    verbose: bool = False,
) -> Any:
    resp = http_request(
        base_url=base_url,
        path=path,
        method="POST",
        token=token,
        json_body=json_body,
        headers=headers,
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    try:
        return json.loads(resp.body.decode("utf-8"))
    except Exception as exc:
        raise ApiError(f"Invalid JSON response from POST {path}") from exc


# -------------------------
# Tabidoo operations
# -------------------------

def verify_token(base_url: str, token: str, timeout_sec: int, verbose: bool) -> dict[str, Any]:
    payload = http_get_json(
        base_url=base_url,
        path="/v2/users/me",
        token=token,
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    user = unwrap_tabidoo_data(payload)
    if not isinstance(user, dict) or "id" not in user:
        return {"raw": user}
    return user


def list_apps(base_url: str, token: str, timeout_sec: int, verbose: bool) -> list[dict[str, Any]]:
    payload = http_get_json(
        base_url=base_url,
        path="/v2/apps",
        token=token,
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    apps = unwrap_tabidoo_data(payload)
    if not isinstance(apps, list):
        raise ApiError("Unexpected /v2/apps response shape (expected list).")
    return [a for a in apps if isinstance(a, dict)]


def get_app_full(base_url: str, token: str, app_id: str, timeout_sec: int, verbose: bool) -> dict[str, Any]:
    payload = http_get_json(
        base_url=base_url,
        path=f"/v2/apps/{app_id}",
        token=token,
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    app = unwrap_tabidoo_data(payload)
    if not isinstance(app, dict):
        raise ApiError("Unexpected /v2/apps/{id} response shape (expected object).")
    return app


def get_typescript_definitions(
    base_url: str,
    token: str,
    app_id: str,
    language: str,
    timeout_sec: int,
    verbose: bool,
) -> str:
    payload = http_post_json(
        base_url=base_url,
        path="/application/getApplicationTypeScriptDefinition",
        token=token,
        json_body={"onlyJsFunctions": False},
        headers={"appinfo": build_appinfo_header(app_id, language=language)},
        timeout_sec=timeout_sec,
        verbose=verbose,
    )
    if isinstance(payload, dict) and "content" in payload and isinstance(payload["content"], str):
        return payload["content"]
    unwrapped = unwrap_tabidoo_data(payload)
    if isinstance(unwrapped, dict) and "content" in unwrapped and isinstance(unwrapped["content"], str):
        return unwrapped["content"]
    raise ApiError("Unexpected TypeScript definition response (missing 'content').")


def try_get_table_data(
    base_url: str,
    token: str,
    app_id: str,
    table_internal: str,
    timeout_sec: int,
    verbose: bool,
) -> Optional[list[dict[str, Any]]]:
    try:
        payload = http_get_json(
            base_url=base_url,
            path=f"/v2/apps/{app_id}/tables/{table_internal}/data",
            token=token,
            timeout_sec=timeout_sec,
            verbose=verbose,
        )
        data = unwrap_tabidoo_data(payload)
        if not isinstance(data, list):
            return None
        return [r for r in data if isinstance(r, dict)]
    except CliError:
        return None


# -------------------------
# LLM scripts extraction
# -------------------------

@dataclass(frozen=True)
class ExtractedCodeFragment:
    table: str
    field_name: str
    code_js: str
    code_ts: str


@dataclass(frozen=True)
class ExtractedCode:
    app_id: str
    app_name: str
    fragments: list[ExtractedCodeFragment]


@dataclass(frozen=True)
class ExtractedWorkflowCodeFragment:
    workflow: str
    triggers: str
    code_js: str
    code_ts: str


@dataclass(frozen=True)
class ExtractedCustomScriptCodeFragment:
    name: str
    namespace: str
    interface: str
    dts: str
    script: str


def extract_executable_code(app_structure: dict[str, Any]) -> ExtractedCode:
    app_id = str(app_structure.get("id", ""))
    app_name = f"{app_structure.get('name', '')} ({app_structure.get('internalName', '')})".strip()

    fragments: list[ExtractedCodeFragment] = []
    tables = app_structure.get("tables") or []
    if not isinstance(tables, list):
        tables = []

    for table in tables:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("internalNameApi", "")) or str(table.get("id", "")) or "unknown_table"
        items = table.get("items") or []
        if not isinstance(items, list):
            items = []

        for field in items:
            if not isinstance(field, dict):
                continue
            field_type = field.get("type")
            field_name = str(field.get("name", ""))

            metadata = field.get("metadata") if isinstance(field.get("metadata"), dict) else {}
            script_meta = metadata.get("script") if isinstance(metadata.get("script"), dict) else {}
            freehtml_meta = (
                metadata.get("freeHtmlInitScript")
                if isinstance(metadata.get("freeHtmlInitScript"), dict)
                else {}
            )

            def push_from(meta: dict[str, Any]) -> None:
                js = meta.get("jsScript")
                if isinstance(js, str) and js.strip():
                    ts = meta.get("tsScript")
                    fragments.append(
                        ExtractedCodeFragment(
                            table=table_name,
                            field_name=field_name,
                            code_js=js,
                            code_ts=ts if isinstance(ts, str) else "",
                        )
                    )

            if field_type in ("calculatedfield", "buttonform"):
                push_from(script_meta)
            if field_type == "freehtmlinput":
                push_from(freehtml_meta)

        scripts = table.get("scripts") or []
        if isinstance(scripts, list):
            for script in scripts:
                if not isinstance(script, dict):
                    continue
                js = script.get("jsScript")
                if isinstance(js, str) and js.strip():
                    ts = script.get("tsScript")
                    fragments.append(
                        ExtractedCodeFragment(
                            table=table_name,
                            field_name=str(script.get("name", "table_script")),
                            code_js=js,
                            code_ts=ts if isinstance(ts, str) else "",
                        )
                    )

    return ExtractedCode(app_id=app_id, app_name=app_name, fragments=fragments)


def extract_executable_code_from_workflows(
    workflows: list[dict[str, Any]],
) -> list[ExtractedWorkflowCodeFragment]:
    extracted: list[ExtractedWorkflowCodeFragment] = []
    for record in workflows:
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        wf_name = str(fields.get("name", ""))
        definition = fields.get("definition") if isinstance(fields.get("definition"), dict) else {}
        triggers = definition.get("triggers")
        triggers_json = json.dumps(triggers, ensure_ascii=True) if triggers is not None else "[]"
        steps = definition.get("steps") if isinstance(definition.get("steps"), list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            if step.get("type") != "jsScript":
                continue
            data = step.get("data") if isinstance(step.get("data"), dict) else {}
            script = data.get("script") if isinstance(data.get("script"), dict) else {}
            code_js = script.get("runableSript") if isinstance(script.get("runableSript"), str) else ""
            code_ts = script.get("writtenTypeScript") if isinstance(script.get("writtenTypeScript"), str) else ""
            extracted.append(
                ExtractedWorkflowCodeFragment(
                    workflow=wf_name,
                    triggers=triggers_json,
                    code_js=code_js,
                    code_ts=code_ts,
                )
            )
    return extracted


def extract_executable_code_from_custom_scripts(
    custom_scripts: list[dict[str, Any]],
) -> list[ExtractedCustomScriptCodeFragment]:
    extracted: list[ExtractedCustomScriptCodeFragment] = []
    for record in custom_scripts:
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        dts = fields.get("dts") if isinstance(fields.get("dts"), dict) else {}
        script = fields.get("script") if isinstance(fields.get("script"), dict) else {}
        extracted.append(
            ExtractedCustomScriptCodeFragment(
                name=str(fields.get("name", "")),
                namespace=str(fields.get("namespace", "")),
                interface=str(fields.get("interface", "")),
                dts=str(dts.get("runableSript", "")) if dts.get("runableSript") is not None else "",
                script=str(script.get("runableSript", "")) if script.get("runableSript") is not None else "",
            )
        )
    return extracted


def format_extracted_code_for_llm(
    extracted_code: ExtractedCode,
    workflows: list[ExtractedWorkflowCodeFragment] | None = None,
    custom_scripts: list[ExtractedCustomScriptCodeFragment] | None = None,
) -> str:
    sections: list[str] = [
        (
            "# Application Code Analysis\n\n"
            f"**Application ID:** {extracted_code.app_id}\n"
            f"**Application Name:** {extracted_code.app_name}\n\n"
        )
    ]

    for idx, block in enumerate(extracted_code.fragments, start=1):
        sections.append(f"## Code Block {idx}\n")
        sections.append(f"**Table:** {block.table}")
        sections.append(f"**Field:** {block.field_name}\n")
        sections.append("```typescript\n")
        sections.append(block.code_ts or "")
        sections.append("```\n")

    if workflows:
        sections.append("## Workflow Code\n\n")
        for idx, wf in enumerate(workflows, start=1):
            sections.append(f"### Workflow {idx}: {wf.workflow}\n")
            sections.append(f"**Triggers:** {wf.triggers}\n")
            sections.append("```typescript\n")
            sections.append(wf.code_ts or "")
            sections.append("```\n")

    if custom_scripts:
        sections.append("## Custom Scripts\n\n")
        for idx, cs in enumerate(custom_scripts, start=1):
            sections.append(f"### Custom Script {idx}: {cs.name}\n")
            sections.append(f"**Namespace:** {cs.namespace}\n")
            sections.append(f"**Interface:** {cs.interface}\n")
            sections.append("```typescript\n")
            sections.append(cs.script or "")
            sections.append("```\n")

    return "\n".join(sections)


# -------------------------
# CLI selection + IO
# -------------------------

def print_apps(apps: list[dict[str, Any]]) -> None:
    print("\nAvailable apps:")
    for idx, app in enumerate(apps, start=1):
        app_id = str(app.get("id", ""))
        name = str(app.get("name", ""))
        internal = str(app.get("internalName", ""))
        print(f"  {idx:>2}) {name} ({internal})  id={app_id}")
    print()


def select_app_interactive(apps: list[dict[str, Any]]) -> dict[str, Any]:
    if not apps:
        raise UserInputError("No apps available for this token.")

    if len(apps) == 1:
        return apps[0]

    print_apps(apps)
    while True:
        choice = input("Select app (number or app id): ").strip()
        if not choice:
            continue

        for app in apps:
            if str(app.get("id", "")) == choice:
                return app

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(apps):
                return apps[idx - 1]

        print("Invalid selection. Try again.")


def choose_app(
    *,
    apps: list[dict[str, Any]],
    app_id: str | None,
    non_interactive: bool,
) -> dict[str, Any]:
    if app_id:
        for app in apps:
            if str(app.get("id", "")) == app_id:
                return app
        raise UserInputError(f"--app-id {app_id} not found among accessible apps.")

    if len(apps) == 1:
        return apps[0]

    if non_interactive:
        raise UserInputError("Multiple apps available; provide --app-id (or run without --no-interactive).")

    return select_app_interactive(apps)


def write_outputs(
    *,
    out_dir: Path,
    app_meta: dict[str, Any],
    base_url: str,
    tsd_content: str,
    llm_md: str,
) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    app_id = str(app_meta.get("id", "unknown"))
    app_name = str(app_meta.get("name", ""))
    internal = str(app_meta.get("internalName", "")) or app_name
    folder = out_dir / f"{app_id}__{sanitize_for_fs(internal)}"
    folder.mkdir(parents=True, exist_ok=True)

    meta_path = folder / "01_app_meta.json"
    tsd_path = folder / "10_types.d.ts"
    llm_path = folder / "20_llm_scripts.md"

    meta_payload = {
        "id": app_id,
        "name": app_name,
        "internalName": str(app_meta.get("internalName", "")),
        "isMultiLanguage": app_meta.get("isMultiLanguage", None),
        "namesI18n": app_meta.get("namesI18n", None),
        "baseUrl": base_url,
    }

    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    tsd_path.write_text(tsd_content or "", encoding="utf-8")
    llm_path.write_text(llm_md or "", encoding="utf-8")

    return meta_path, tsd_path, llm_path


# -------------------------
# Main
# -------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="tabidoo_llm_export.py",
        description="Export Tabidoo app .d.ts + LLM scripts markdown (standalone).",
    )
    p.add_argument("--app-id", help="Select app by id (skips interactive selection).")
    p.add_argument("--out-dir", default="./out", help="Output directory root (default: ./out).")
    p.add_argument("--base-url", help="Force Tabidoo API base URL (default: https://app.tabidoo.cloud).")
    p.add_argument("--language", default="en", help="Language for appinfo header (default: en).")
    p.add_argument(
        "--no-interactive",
        "--yes",
        dest="no_interactive",
        action="store_true",
        help="Do not prompt; fail if --app-id is missing and multiple apps exist.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help=f"HTTP timeout seconds (default: {DEFAULT_TIMEOUT_SEC}).",
    )
    p.add_argument("--verbose", action="store_true", help="Print request URLs (no secrets).")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env")

    token = os.environ.get("TABIDOO_API_KEY", "").strip()
    if not token:
        raise InvalidConfigError("Missing TABIDOO_API_KEY. Put it into .env next to the script.")

    args = parse_args(argv)
    base_url = normalize_base_url(args.base_url) if args.base_url else DEFAULT_BASE_URL

    user = verify_token(base_url, token, timeout_sec=args.timeout, verbose=args.verbose)
    user_email = user.get("email") if isinstance(user, dict) else None
    print(f"Using instance: {base_url}")
    if user_email:
        print(f"Authenticated as: {user_email}")

    apps = list_apps(base_url, token, timeout_sec=args.timeout, verbose=args.verbose)
    if not apps:
        raise UserInputError("No apps returned for this token.")

    selected = choose_app(apps=apps, app_id=args.app_id, non_interactive=args.no_interactive)
    app_id = str(selected.get("id", ""))
    if not app_id:
        raise ApiError("Selected app is missing 'id'.")

    print(f"\nSelected app: {selected.get('name')} ({selected.get('internalName')}) id={app_id}\n")

    print("Fetching TypeScript definitions (.d.ts)...")
    tsd = get_typescript_definitions(
        base_url,
        token,
        app_id,
        language=args.language,
        timeout_sec=args.timeout,
        verbose=args.verbose,
    )

    print("Fetching app structure + workflows + custom scripts...")
    app_full = get_app_full(base_url, token, app_id, timeout_sec=args.timeout, verbose=args.verbose)
    workflows_table = try_get_table_data(
        base_url,
        token,
        app_id,
        "wascenarios",
        timeout_sec=args.timeout,
        verbose=args.verbose,
    )
    custom_scripts_table = try_get_table_data(
        base_url,
        token,
        app_id,
        "customScripts",
        timeout_sec=args.timeout,
        verbose=args.verbose,
    )

    extracted = extract_executable_code(app_full)
    workflows = extract_executable_code_from_workflows(workflows_table) if workflows_table else []
    custom_scripts = extract_executable_code_from_custom_scripts(custom_scripts_table) if custom_scripts_table else []

    llm_md = format_extracted_code_for_llm(extracted, workflows=workflows, custom_scripts=custom_scripts)

    out_dir = Path(args.out_dir).expanduser().resolve()
    meta_path, tsd_path, llm_path = write_outputs(
        out_dir=out_dir,
        app_meta=selected,
        base_url=base_url,
        tsd_content=tsd,
        llm_md=llm_md,
    )

    print("Done.\n")
    print("Wrote:")
    print(f"  - {meta_path}")
    print(f"  - {tsd_path}")
    print(f"  - {llm_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except CliError as exc:
        eprint(f"ERROR: {exc}")
        raise SystemExit(exc.exit_code)
    except KeyboardInterrupt:
        eprint("Cancelled.")
        raise SystemExit(130)
