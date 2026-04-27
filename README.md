# Tabidoo LLM Export CLI (Python)

Standalone Python CLI that exports Tabidoo application context into LLM-ready files with a rich, interactive UX.

## What it does

1. Load `TABIDOO_API_TOKEN` from a `.env` file in your working directory (or from the process environment).
2. Validate the configuration and list accessible apps.
3. Let you pick an app (or continue automatically if only one exists).
4. Download:
   - Full schema definitions (`schema.md`)
   - Official tables overview (`tables.md`)
   - "All scripts for LLM" (`scripts.md`)
5. Write outputs to a predictable folder structure.

## Output layout

Default output (overridable via CLI flags):

```
./out/<app-name>-schema.md
./out/<app-name>-tables.md
./out/<app-name>-scripts.md
```

### File contents

- `<app-name>-schema.md`
  - Per-table schema definitions wrapped in a Markdown TypeScript block
- `<app-name>-tables.md`
  - Markdown overview grouped by modules with table metadata and field navigation
- `<app-name>-scripts.md`
  - Markdown bundle of app scripts prepared for LLM input, including table scripts, field formulas, button scripts, free HTML field code, workflows, and custom scripts

## Requirements

- Python 3.11+ (3.10 should work if typing stays minimal)
- Dependencies (installed via `uv`):
  - `python-dotenv` (robust `.env` parsing)
  - `rich` (nicer interactive UI)
  - `typer` (CLI UX and options)

## Quick start

0) Install dependencies:

```bash
uv sync
```

1) Create `.env` in your working directory:

```bash
TABIDOO_API_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
```

2) Run interactively (via UV):

```bash
uv run tabidoo-llm-export
```

3) Optional shortcut script (installs deps + runs the CLI):

```bash
./scripts/run.sh
```

4) Non-interactive:

```bash
uv run tabidoo-llm-export --app-id <APP_ID> --out-dir ./out --yes
```

Alternative entry points:

```bash
uv run python -m tabidoo_llm_export
uv run python tabidoo_llm_export.py
```

## CLI flags

- `--app-id <id>`
  - Skip selection and export a specific app.
- `--out-dir <path>` (default: `./out`)
  - Output root directory.
- `--yes` / `--no-interactive`
  - Do not prompt; fail if `--app-id` is missing and multiple apps exist.
- `--base-url <url>`
  - Force API base URL (defaults to `https://app.tabidoo.cloud/api`).
- `--language <code>`
  - Language used in request headers (default: `en`).
- `--timeout <seconds>`
  - HTTP timeout (default: 30).
- `--verbose`
  - Print request/response info (never print the token).

## API endpoints used

The CLI talks directly to Tabidoo API endpoints:

- `GET /v2/users/me` (token validation)
- `GET /v2/apps`
- `GET /v2/apps/{appId}`
- `POST /v2/apps/getApplicationTypeScriptDefinition` (for `schema.md`, called per table with `schemaId`)
- `GET /v2/apps/{appId}/tables/customScripts/data` (optional)
- `GET /v2/apps/{appId}/tables/wascenarios/data` (optional)

## Error handling and exit codes

Recommended exit codes:

- `0` success
- `2` invalid config (missing env var, invalid `.env`)
- `3` auth error (token invalid / unauthorized)
- `4` network error (timeouts, DNS)
- `5` API error (unexpected response or non-auth 4xx/5xx)
- `6` user input error (invalid selection, missing `--app-id` in non-interactive)

## Security notes

- Never print the token.
- Never write the token to disk.
- Redact auth headers in verbose logs.

## Troubleshooting

- 401 / 403:
  - Verify `TABIDOO_API_TOKEN` is correct and has access to the target apps.
  - If only `schema.md` is missing, verify token permissions and app access for `/v2/apps/getApplicationTypeScriptDefinition`.
- No apps returned:
  - The token might be scoped to a different instance or base URL.
- Try `--base-url` explicitly (use `https://app.tabidoo.cloud/api`).
- Odd output folder names:
  - App names are sanitized for filesystem safety.

## Implementation notes (for the agent building the script)

- Multi-file package for clarity (`tabidoo_llm_export/`).
- Favor deterministic output names and ordering.
- Keep HTTP helpers small and testable.
- If base URL autodetection is added, validate against `/v2/users/me` and default to `https://app.tabidoo.cloud` when unspecified.
