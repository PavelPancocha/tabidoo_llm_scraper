# Tabidoo LLM Export CLI (Python)

Standalone Python CLI that exports Tabidoo application context into LLM-ready files.

## What it does

1. Load `TABIDOO_API_KEY` from a `.env` file placed next to the script (or from the process environment).
2. Validate the configuration and list accessible apps.
3. Let you pick an app (or continue automatically if only one exists).
4. Download:
   - TypeScript definitions (`.d.ts`)
   - "All scripts for LLM" (Markdown)
5. Write outputs to a predictable folder structure.

## Output layout

Default output (overridable via CLI flags):

```
./out/<appId>__<appName>/
01_app_meta.json
10_types.d.ts
20_llm_scripts.md
```

### File contents

- `01_app_meta.json`
  - App id, name, internalName (and base URL if captured)
- `10_types.d.ts`
  - Raw TypeScript definition content
- `20_llm_scripts.md`
  - Markdown bundle of app scripts prepared for LLM input

## Requirements

- Python 3.11+ (3.10 should work if typing stays minimal)
- Prefer standard library only
  - If you add dependencies, keep them minimal and document them

## Quick start

1) Create `.env` next to the script:

```
TABIDOO_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
```

2) Run interactively:

```bash
python tabidoo_llm_export.py
```

3) Non-interactive:

```bash
python tabidoo_llm_export.py --app-id <APP_ID> --out-dir ./out --yes
```

## CLI flags (planned)

- `--app-id <id>`
  - Skip selection and export a specific app.
- `--out-dir <path>` (default: `./out`)
  - Output root directory.
- `--yes` / `--no-interactive`
  - Do not prompt; fail if `--app-id` is missing and multiple apps exist.
- `--base-url <url>`
  - Force API base URL (useful if autodetection fails).
- `--verbose`
  - Print request/response info (never print the token).

## API endpoints used

The CLI talks directly to Tabidoo API endpoints:

- `GET /v2/users/me` (token validation)
- `GET /v2/apps`
- `GET /v2/apps/{appId}`
- `POST /application/getApplicationTypeScriptDefinition`
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

- Never print the API key.
- Never write the API key to disk.
- Redact auth headers in verbose logs.

## Troubleshooting

- 401 / 403:
  - Verify `TABIDOO_API_KEY` is correct and has access to the target apps.
- No apps returned:
  - The token might be scoped to a different instance or base URL.
  - Try `--base-url` explicitly.
- Odd output folder names:
  - App names are sanitized for filesystem safety.

## Implementation notes (for the agent building the script)

- Keep it a single-file script.
- Favor deterministic output names and ordering.
- Keep HTTP helpers small and testable.
- If base URL autodetection is added, validate against `/v2/users/me` and default to `https://app.tabidoo.cloud` when unspecified.
