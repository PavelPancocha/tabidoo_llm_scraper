# Tabidoo LLM Export CLI - Technical Documentation

## Project Overview

**Tabidoo LLM Export CLI** is a standalone Python command-line tool that exports Tabidoo application context into Markdown files optimized for LLM consumption and human navigation.

### Purpose

The tool bridges Tabidoo's low-code platform with AI-assisted development by:
- Exporting the full FE-only schema definition into `*-schema.md` when `TABIDOO_FE_TOKEN` is available
- Exporting an official API-based tables overview into `*-tables.md`
- Collecting custom scripts, workflows, and field-level code into `*-scripts.md`
- Producing deterministic, reviewable Markdown outputs with a simple CLI UX

### Key Capabilities

1. **Hybrid Authentication**: Uses `TABIDOO_API_TOKEN` for documented read endpoints and optional `TABIDOO_FE_TOKEN` for full schema definition export
2. **Interactive Selection**: Lists accessible apps and allows user selection
3. **Comprehensive Extraction**: Downloads workflows, custom scripts, field-level code, and optional full schema definitions
4. **Navigation-Friendly Output**: Generates both a compact table/field overview and an LLM-oriented scripts bundle
5. **Partial Export Support**: Produces `tables.md` and `scripts.md` even when full schema export is unavailable

---

## Architecture Overview

### Technology Stack

- **Python**: 3.13+ (3.11+ supported)
- **Package Manager**: `uv`
- **Key Dependencies**:
  - `typer` - CLI framework with type hints
  - `rich` - Terminal UI (progress bars, colors, tables)
  - `python-dotenv` - Environment variable management

### Module Structure

```
tabidoo_llm_export/
├── __init__.py          # Package initialization
├── __main__.py          # Python -m entry point
├── cli.py               # CLI command definition (Typer)
├── runner.py            # Main export orchestration
├── api.py               # Tabidoo API client & optional FE TSD fetcher
├── http_client.py       # HTTP request handling
├── extractor.py         # Script/code extraction logic
├── formatters.py        # Markdown formatting for schema/tables/scripts
├── output.py            # File writing operations
├── models.py            # Data models (dataclasses)
├── errors.py            # Custom exception hierarchy
├── constants.py         # Constants, enums, text messages
├── env.py               # Environment & token management
├── ui.py                # User interface (Rich console)
└── stats.py             # Statistics computation
```

---

## Detailed Module Documentation

### 1. **cli.py** - Command-Line Interface

**Purpose**: Defines the Typer application and main command entry point.

**Key Components**:
- `export()` command with CLI options
- Options: `--app-id`, `--out-dir`, `--base-url`, `--language`, `--no-interactive`, `--timeout`, `--verbose`
- Loads `.env`, resolves the primary read token, optionally resolves FE token for full schema export
- Delegates execution to `ExportRunner`

**Flow**:
1. Display banner
2. Load `.env`
3. Read `TABIDOO_API_TOKEN` or fallback `TABIDOO_FE_TOKEN`
4. Read optional `TABIDOO_FE_TOKEN` for full schema export
5. Normalize base URL
6. Create and run `ExportRunner`
7. Handle errors with appropriate exit codes

**Exit Codes**:
- `0` - Success
- `2` - Invalid configuration
- `3` - Authentication error
- `4` - Network error
- `5` - API error
- `6` - User input error
- `130` - Cancelled (Ctrl+C)

---

### 2. **runner.py** - Export Orchestration

**Purpose**: Coordinates the full export flow and handles partial export when FE-only schema export is unavailable.

**Class**: `ExportRunner`

**Process Flow**:
1. **Authenticate** via `/v2/users/me` using the primary read token
2. **Load Apps** via `/v2/apps`
3. **Select App** interactively or through `--app-id`
4. **Load App Details** via `/v2/apps/{appId}`
5. **Fetch Full Schema Definitions** via FE-only endpoint when `TABIDOO_FE_TOKEN` is present
6. **Build Tables Overview** from official app metadata (`modules`, `tables`, `items`)
7. **Fetch Workflows** from `wascenarios`
8. **Fetch Custom Scripts** from `customScripts`
9. **Extract Code** from tables, fields, workflows, and custom scripts
10. **Write Files** to `{app-name}-schema.md` (optional), `{app-name}-tables.md`, `{app-name}-scripts.md`

**Partial Export Behavior**:
- If FE token is missing or the FE schema endpoint fails, the run continues.
- `schema.md` is skipped, any stale old schema file is removed, and `tables.md` / `scripts.md` are still written.

**Return Value**: Tuple of `(schema_path | None, tables_path, scripts_path)`

---

### 3. **api.py** - Tabidoo API Integration

**Classes**:

#### `TabidooApi`
Core API client wrapping documented HTTP requests.

**Methods**:
- `get_user()` - Validate token and get user info
- `list_apps()` - List accessible applications
- `get_app_full(app_id)` - Get complete app structure including `modules`, `tables`, `items`, and table scripts
- `get_table_data(app_id, table_internal)` - Get paginated data from system tables (`wascenarios`, `customScripts`)
- `get_typescript_definition(app_id, language, schema_id, headers)` - Optional FE-only full schema definition fetch

**Key Features**:
- JSON unwrapping (`{data: ...}`)
- Pagination for `/tables/{table}/data` via `limit` + `skip`
- Typed error handling

#### `TsdFetcher`
Optional FE-only fetcher for `/application/getApplicationTypeScriptDefinition`.

**Features**:
- Uses browser-like headers (`Origin`, `Referer`, `Accept-Language`, `appinfo`)
- Fetches per-table schema definitions and concatenates them into one `schema.md` payload
- Used only when `TABIDOO_FE_TOKEN` is available

---

### 4. **extractor.py** - Code Extraction

**Class**: `ScriptExtractor`

**Responsibilities**:
- Extract field and table scripts from app structure
- Extract workflow scripts from `wascenarios`
- Extract custom scripts from `customScripts`

**Important Behavior**:
- Supports both JS-only and TS-only field/table scripts
- Recurses through nested workflow containers such as `foreach -> workflowDefinition -> steps`
- Preserves custom script `.d.ts` definitions alongside runnable code

---

### 5. **formatters.py** - Markdown Formatting

**Classes**:

#### `LlmFormatter`
Formats extracted code into the final `*-scripts.md` bundle.

**Important Behavior**:
- Renders TypeScript when present
- Falls back to JavaScript when TypeScript is absent
- Includes custom script definitions (`dts`) and runnable script blocks

#### `TablesFormatter`
Builds `*-tables.md` from official app metadata.

**Output Shape**:
- App metadata header
- Tables grouped by modules when module mappings are available
- Fallback `Ungrouped Tables` section for tables not assigned to any module
- Per-table Markdown table with: field label, internal name, type, required flag, description

#### `MarkdownRenderer`
Wraps the FE-only full schema definition into a Markdown TypeScript code fence for `*-schema.md`.

---

### 6. **http_client.py** - HTTP Communication

**Class**: `HttpClient`

**Features**:
- URL building with `urljoin`
- Automatic Bearer token injection
- JSON request/response handling
- HTTP error parsing with user-friendly messages
- Verbose mode (prints URLs without exposing tokens)
- Timeout support

**Error Handling**:
- `401/403` → `AuthError`
- Other HTTP errors → `HttpStatusError`
- Network errors (DNS, timeout) → `NetworkError`
- JSON parsing errors → `ApiError`

**Error Message Formatting**:
- Extracts `{errors: [{message: "..."}]}` from API responses
- Trims long error bodies with ellipsis
- Provides context (URL, status code)

---

### 7. **models.py** - Data Models

**Dataclasses** (all frozen, immutable):

#### `HttpResponse`
```python
status: int
headers: dict[str, str]
body: bytes
```

#### `AppSummary`
```python
app_id: str
name: str
internal_name: str
```

#### `ExtractedCodeFragment`
```python
table: str
field_name: str
code_js: str
code_ts: str
```

#### `ExtractedCode`
```python
app_id: str
app_name: str
fragments: list[ExtractedCodeFragment]
```

#### `ExtractedWorkflowCodeFragment`
```python
workflow: str
triggers: str  # JSON string
code_js: str
code_ts: str
```

#### `ExtractedCustomScriptCodeFragment`
```python
name: str
namespace: str
interface: str
dts: str  # TypeScript definitions
script: str  # Runnable code
```

#### `ExportStats`
```python
tables: int
fields: int
code_blocks: int
workflows: int
custom_scripts: int
schema_lines: int
schema_bytes: int
tables_md_lines: int
tables_md_bytes: int
llm_lines: int
llm_bytes: int
```

---

### 8. **errors.py** - Exception Hierarchy

**Base**: `CliError(Exception)`
- `exit_code: ExitCode` attribute

**Subclasses**:
- `InvalidConfigError` - Exit code 2
- `AuthError` - Exit code 3
- `NetworkError` - Exit code 4
- `ApiError` - Exit code 5
- `UserInputError` - Exit code 6
- `HttpStatusError(ApiError)` - Includes HTTP status

**Usage**: Raise specific errors to trigger appropriate exit codes and error messages.

---

### 9. **constants.py** - Configuration & Messages

**Categories**:

#### Enums
- `ExitCode` - Exit codes (0, 2-6, 130)
- `HttpStatus` - HTTP status codes
- `HttpMethod` - GET, POST
- `Encoding` - UTF-8
- `FieldType` - calculatedfield, buttonform, freehtmlinput
- `WorkflowStepType` - jsScript
- `TableInternal` - wascenarios, customScripts

#### Defaults
- `Defaults.BASE_URL` - `https://app.tabidoo.cloud/api`
- `Defaults.OUT_DIR` - `./out`
- `Defaults.LANGUAGE` - `en`
- `Defaults.TIMEOUT_SEC` - `30`
- `Defaults.TABLE_DATA_PAGE_LIMIT` - `1000`

#### Text Messages
- `Text.TITLE`, `Text.DONE`, `Text.AUTHENTICATING`, etc.
- User-facing messages with emoji icons
- Error messages with formatting placeholders

#### API Endpoints
- `Endpoint.USERS_ME` - `/v2/users/me`
- `Endpoint.APPS` - `/v2/apps`
- `Endpoint.APP_DETAIL` - `/v2/apps/{app_id}`
- `Endpoint.TSD` - `/application/getApplicationTypeScriptDefinition` (optional, FE-only)
- `Endpoint.TABLE_DATA` - `/v2/apps/{app_id}/tables/{table}/data`

#### Markdown Templates
- `MarkdownText.*` - Markdown formatting strings

---

### 10. **env.py** - Configuration Management

**Classes**:

#### `EnvLoader`
Loads `.env` files using `python-dotenv` or fallback parser.

**Fallback Parser**:
- Handles `KEY=value` format
- Strips quotes (single/double)
- Skips comments (`#`)
- Only sets if not already in environment

#### `TokenProvider`
Resolves tokens from environment.

**Behavior**:
- `read()` prefers `TABIDOO_API_TOKEN`, then falls back to `TABIDOO_FE_TOKEN`
- `read_fe_optional()` returns `TABIDOO_FE_TOKEN` only, or `None`
- Raises `InvalidConfigError` only when neither token is available

#### `UrlNormalizer`
Normalizes and validates base URLs.

**Transformations**:
- Strip whitespace
- Ensure `http://` or `https://` prefix
- Remove trailing slashes
- Strip `/v2` suffix if present
- Append `/api` if missing

**Example**:
- `https://app.tabidoo.cloud` → `https://app.tabidoo.cloud/api`
- `https://app.tabidoo.cloud/api/v2` → `https://app.tabidoo.cloud/api`

#### `JsonUnwrapper`
Unwraps `{data: ...}` API responses.

#### `AppInfoBuilder`
Builds `appinfo` header JSON:
```json
{
  "appId": "...",
  "language": "en",
  "customData": {},
  "browserLanguage": ""
}
```

#### `Sanitizer`
Sanitizes app names for filenames:
- Lowercase
- Replace whitespace with `_`
- Remove invalid chars (only keep `a-z0-9_-.`)
- Strip leading/trailing `._-`
- Fallback to `"app"` if empty

#### `Encoder`
URL-encodes strings (wraps `urllib.parse.quote`).

---

### 11. **ui.py** - User Interface

**Class**: `Ui`

**Methods**:
- `banner()` - Display title banner
- `progress()` - Create Rich progress context
- `info(msg)`, `success(msg)`, `warning(msg)`, `error(msg)` - Colored output
- `show_stats(stats)` - Display statistics table

**Class**: `AppSelector`

**Method**: `select(apps, app_id, non_interactive)`

**Logic**:
1. If `app_id` provided, find matching app
2. If one app available, auto-select
3. If `non_interactive`, fail if multiple apps
4. Otherwise, show interactive table and prompt

**Display**: Rich table with columns: `#`, `Name`, `Internal`, `ID`

---

### 12. **output.py** - File Writing

**Class**: `OutputWriter`

**Method**: `write(out_dir, app, schema_md, tables_md, llm_md)` → `(schema_path | None, tables_path, scripts_path)`

**Process**:
1. Create output directory (with parents)
2. Sanitize app name for filename
3. Generate filenames:
   - `{sanitized_name}-schema.md`
   - `{sanitized_name}-tables.md`
   - `{sanitized_name}-scripts.md`
4. Wrap full schema definition into a Markdown TypeScript block
5. If schema export is skipped, remove any stale old schema file
6. Write files with UTF-8 encoding

**Output Structure**:
```
./out/
├── my_app-schema.md    # Full schema definition (optional)
├── my_app-tables.md    # Official API-based tables overview
└── my_app-scripts.md   # Application code analysis
```

---

### 13. **stats.py** - Statistics Calculation

**Class**: `StatsBuilder`

**Method**: `build(app_full, extracted, workflows, custom_scripts, schema_md, tables_md, llm_md)` → `ExportStats`

**Computed Metrics**:
- **Tables** - Count from app structure
- **Fields** - Count from app structure
- **Code blocks** - Number of extracted code fragments
- **Workflow scripts** - Number of workflow code fragments
- **Custom scripts** - Number of custom script fragments
- **Schema lines** - Line count in `schema.md`
- **Schema bytes** - Byte size of `schema.md`
- **Tables MD lines** - Line count in `tables.md`
- **Tables MD bytes** - Byte size of `tables.md`
- **LLM lines** - Line count in formatted output
- **LLM bytes** - Byte size of formatted output

---

## API Integration Details

### Authentication

**Method**: Bearer token (JWT)

**Primary Token**:
- `TABIDOO_API_TOKEN` generated in Tabidoo user settings
- Used for all documented read endpoints used by the exporter

**Optional Token**:
- `TABIDOO_FE_TOKEN` from browser localStorage
- Used only for `/application/getApplicationTypeScriptDefinition` to create full `schema.md`

**Token Storage**:
- Store `TABIDOO_API_TOKEN` in `.env`
- Add `TABIDOO_FE_TOKEN` only if full schema export is needed

**Security**:
- Never print token in logs
- Never write token to output files
- Redact Authorization header in verbose mode

---

### API Endpoints

#### 1. **GET /v2/users/me**
Validates token and retrieves user information.

**Response**:
```json
{
  "data": {
    "id": "user_id",
    "email": "user@example.com",
    ...
  }
}
```

#### 2. **GET /v2/apps**
Lists all accessible applications.

**Response**:
```json
{
  "data": [
    {
      "id": "app_id",
      "name": "App Name",
      "internalName": "app_internal"
    }
  ]
}
```

#### 3. **GET /v2/apps/{appId}**
Gets full application structure.

**Response**:
```json
{
  "data": {
    "id": "app_id",
    "name": "App Name",
    "internalName": "app_internal",
    "modules": [
      {
        "header": "Module Name",
        "tableIds": ["table_id"]
      }
    ],
    "tables": [
      {
        "id": "table_id",
        "header": "Table Name",
        "internalNameApi": "table_name",
        "items": [
          {
            "name": "field_name",
            "header": "Field Label",
            "type": "calculatedfield",
            "metadata": {
              "script": {
                "jsScript": "...",
                "tsScript": "..."
              }
            }
          }
        ],
        "scripts": [
          {
            "name": "script_name",
            "jsScript": "...",
            "tsScript": "..."
          }
        ]
      }
    ]
  }
}
```

#### 4. **POST /application/getApplicationTypeScriptDefinition**
Fetches full schema definitions.

**Status**:
- Not part of the documented public API blueprint used by the rest of the exporter
- Requires `TABIDOO_FE_TOKEN`
- Optional in the current runtime; export continues without it

**Request Headers**:
```
Authorization: Bearer {token}
Accept: application/json, text/plain, */*
Accept-Language: en;q=0.6
Origin: {origin}
Referer: {origin}/app/{appInternal}/schema/{tableInternal}
appinfo: {urlencoded_json}
Content-Type: application/json
```

**Request Body**:
```json
{
  "onlyJsFunctions": false,
  "schemaId": "table_id"  // optional, per-table
}
```

**Response**:
```json
{
  "content": "// TypeScript definitions..."
}
```

#### 5. **GET /v2/apps/{appId}/tables/{tableInternal}/data**
Gets data from system tables.

**Table Names**:
- `wascenarios` - Workflows
- `customScripts` - Custom scripts

**Pagination**:
- The runtime fetches these endpoints with `limit` + `skip`
- `wascenarios` defaults to 25 rows server-side if pagination is omitted

**Response**:
```json
{
  "data": [
    {
      "fields": {
        "name": "...",
        "definition": {...},
        ...
      }
    }
  ]
}
```

---

## Configuration

### Environment Variables

**Required**:
- `TABIDOO_API_TOKEN` - API token for documented read endpoints

**Optional**:
- `TABIDOO_FE_TOKEN` - Browser FE token for full `schema.md`

**Optional** (via CLI flags):
- `--base-url` - API base URL (default: `https://app.tabidoo.cloud/api`)
- `--language` - Language code for API headers (default: `en`)
- `--timeout` - HTTP timeout in seconds (default: `30`)

### .env File Format

```bash
# Required: API token from Tabidoo user settings
TABIDOO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional: browser FE token for full schema export
TABIDOO_FE_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional: Override base URL
# BASE_URL=https://custom.tabidoo.instance/api
```

---

## Usage Guide

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd tabidoo_llm_scraper

# Install dependencies
uv sync
```

### Basic Usage

```bash
# Interactive mode (with .env file)
uv run tabidoo-llm-export

# Interactive mode with full schema export
uv run tabidoo-llm-export  # with TABIDOO_FE_TOKEN present

# Non-interactive with specific app
uv run tabidoo-llm-export --app-id ABC123 --yes

# Custom output directory
uv run tabidoo-llm-export --out-dir ./exports

# Verbose mode (show HTTP requests)
uv run tabidoo-llm-export --verbose

# Custom base URL
uv run tabidoo-llm-export --base-url https://custom.tabidoo.cloud/api
```

### Shell Script Wrapper

```bash
# Run with automatic dependency installation
./scripts/run.sh

# Pass arguments to the CLI
./scripts/run.sh --app-id ABC123 --yes
```

### Alternative Entry Points

```bash
# Python module execution
uv run python -m tabidoo_llm_export

# Direct script execution
uv run python tabidoo_llm_export.py
```

---

## Output Files

### File Naming

Files are named using sanitized app names:
- `{sanitized_app_name}-schema.md`
- `{sanitized_app_name}-tables.md`
- `{sanitized_app_name}-scripts.md`

**Sanitization Rules**:
- Convert to lowercase
- Replace spaces with underscores
- Remove special characters (keep only `a-z`, `0-9`, `_`, `-`, `.`)
- Strip leading/trailing `._-`

**Examples**:
- "My App" → `my_app-schema.md`
- "My App" → `my_app-tables.md`
- "CRM System (v2)" → `crm_system_v2-schema.md`

### Schema File (`*-schema.md`)

Contains full FE-only schema definitions wrapped in Markdown:

```markdown
# TypeScript Definitions

```typescript
// Table: users (user_table_id)
declare namespace Users {
  interface Record {
    id: string;
    name: string;
    email: string;
  }
}

// Table: orders (order_table_id)
declare namespace Orders {
  interface Record {
    id: string;
    userId: string;
    total: number;
  }
}
```
```

### Tables File (`*-tables.md`)

Contains a module-grouped overview of tables and fields derived from official app metadata:

```markdown
# Application Tables

**Application ID:** app_123
**Application Name:** My App
**Application Internal Name:** my_app

## Module: Sales

### Table: Customers
**Table Internal Name:** customers
**Table ID:** table_123

| Field Label | Internal Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| Name | `name` | `text` | yes | Customer name |
| Email | `email` | `text` | no | Primary contact email |
```

### Scripts File (`*-scripts.md`)

Contains extracted code blocks, workflows, and custom scripts:

```markdown
# Application Code Analysis

**Application ID:** app_123
**Application Name:** My App (my_app)

## Code Block 1
**Table:** users
**Field:** calculated_age

```typescript
// Calculate age from birthdate
return moment().diff(moment(ctx.record.birthdate), 'years');
```

## Code Block 2
**Table:** orders
**Field:** button_process

```typescript
// Process order button action
await ctx.api.updateRecord('orders', ctx.record.id, {
  status: 'processed'
});
```

## Workflow Code

### Workflow 1: Send Welcome Email
**Triggers:** [{"type":"onCreate","table":"users"}]

```typescript
// Send welcome email to new user
await ctx.email.send({
  to: ctx.record.email,
  subject: 'Welcome!',
  body: `Hello ${ctx.record.name}!`
});
```

## Custom Scripts

### Custom Script 1: Data Validator
**Namespace:** utils
**Interface:** IValidator

```typescript
// Custom validation logic
export function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
```
```

---

## Development Guide

### Project Structure

```
tabidoo_llm_scraper/
├── .env                      # Environment variables (not in git)
├── .venv/                    # Virtual environment (created by uv)
├── pyproject.toml            # Project config & dependencies
├── uv.lock                   # Dependency lock file
├── README.md                 # User documentation
├── CLAUDE.md                 # This file (technical docs)
├── tabidoo_llm_export.py     # Entry point script
├── main.py                   # Alternative entry point
├── scripts/
│   └── run.sh                # Convenience wrapper script
├── tabidoo_llm_export/       # Main package
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── runner.py
│   ├── api.py
│   ├── http_client.py
│   ├── extractor.py
│   ├── formatters.py
│   ├── output.py
│   ├── models.py
│   ├── errors.py
│   ├── constants.py
│   ├── env.py
│   ├── ui.py
│   └── stats.py
└── out/                      # Default output directory (created at runtime)
```

### Adding New Features

#### Adding a New CLI Option

1. Add constant to `constants.py`:
```python
class CliOption:
    NEW_OPTION = ("--new-option",)

class HelpText(StrEnum):
    NEW_OPTION = "Description of new option"
```

2. Add parameter to `cli.py`:
```python
@app.command()
def export(
    # ... existing params ...
    new_option: str = typer.Option("default", *CliOption.NEW_OPTION, help=HelpText.NEW_OPTION),
):
    # Pass to runner
    runner = ExportRunner(..., new_option=new_option)
```

3. Update `ExportRunner.__init__()` in `runner.py`

#### Adding a New API Endpoint

1. Add endpoint to `constants.py`:
```python
class Endpoint(StrEnum):
    NEW_ENDPOINT = "/v2/new/endpoint/{param}"
```

2. Add method to `TabidooApi` in `api.py`:
```python
def get_new_data(self, param: str) -> dict[str, Any]:
    payload = self._client.get_json(Endpoint.NEW_ENDPOINT.format(param=param))
    return JsonUnwrapper.unwrap(payload)
```

#### Adding a New Extractor

1. Add extraction method to `ScriptExtractor` in `extractor.py`:
```python
def extract_new_type(self, data: list[dict[str, Any]]) -> list[NewFragment]:
    extracted = []
    for item in data:
        # Extraction logic
        extracted.append(NewFragment(...))
    return extracted
```

2. Add model to `models.py`:
```python
@dataclass(frozen=True)
class NewFragment:
    field1: str
    field2: str
```

3. Update formatter in `formatters.py` to handle new type

### Testing Considerations

**Current State**: No automated tests yet.

**Recommended Test Structure**:
```
tests/
├── test_env.py               # Test EnvLoader, TokenProvider, etc.
├── test_extractor.py         # Test script extraction logic
├── test_formatters.py        # Test Markdown formatting
├── test_http_client.py       # Mock HTTP requests
├── test_api.py               # Test API client methods
├── test_models.py            # Test dataclass creation
└── fixtures/
    ├── sample_app.json       # Sample API responses
    ├── sample_tsd.ts          # Sample full schema definition payload
    └── sample_tables.md       # Sample module-grouped tables overview
```

**Testing with Real API**:
```bash
# Set up test .env
cat > .env.test << EOF
TABIDOO_API_TOKEN=your_api_token
# optional:
# TABIDOO_FE_TOKEN=your_fe_token
EOF

# Run with test environment
uv run python -c "
import os
os.environ['TABIDOO_API_TOKEN'] = 'test_token'
from tabidoo_llm_export.cli import main
main()
"
```

### Extraction Guardrails

When changing extractors, treat these as mandatory checks:

- **Assume table-data endpoints may be paginated**. Verify whether `/tables/{table}/data` returns only the first page by default, and fetch all rows with `limit` + `skip` until exhausted.
- **Do not assume workflow code lives only in top-level `jsScript` steps**. Workflow containers such as `foreach` can hide executable code inside `data.workflowDefinition.steps`, so workflow extraction must recurse through nested workflow definitions.
- **Do not emit empty code fences when code exists**. If TypeScript is missing but JavaScript exists, render JavaScript instead of an empty TypeScript block.
- **Do not drop custom script definitions**. If a custom script exposes both `dts.runableSript` and `script.runableSript`, export both.
- **Support TS-only and JS-only sources**. Field scripts, free-HTML init scripts, and table scripts should be exported when either `jsScript` or `tsScript` is present.
- **Validate extraction against raw payload shape**. For any “missing script” report, inspect the raw API response first and compare raw script count vs extracted fragment count before changing formatter logic.
- **Add regression fixtures for real failure modes**. Keep fixtures for paginated `wascenarios` / `customScripts`, nested `workflowDefinition`, JS-only blocks, TS-only blocks, and custom scripts with `.d.ts`.

### Code Style

**Type Hints**: Required on all function signatures
```python
def function_name(param: str, optional: Optional[int] = None) -> dict[str, Any]:
    ...
```

**Imports**: Use `from __future__ import annotations` for forward references

**String Formatting**: Use f-strings or `.format()`, no `%` formatting

**Constants**: Use enums (`StrEnum`, `IntEnum`) for related constants

**Immutability**: Prefer frozen dataclasses for data models

**Error Handling**: Raise specific `CliError` subclasses, not generic `Exception`

---

## Error Handling

### Exception Flow

```
User Action
    ↓
CLI Command (cli.py)
    ↓
ExportRunner (runner.py)
    ↓
[API/HTTP/Extractor/etc.]
    ↓
Raise CliError subclass
    ↓
Caught in cli.py
    ↓
Print error message
    ↓
Exit with appropriate code
```

### Error Categories

| Error Type | Exit Code | Common Causes | Resolution |
|------------|-----------|---------------|------------|
| `InvalidConfigError` | 2 | Missing token, invalid URL | Check `.env` file |
| `AuthError` | 3 | Invalid token, expired session | Re-authenticate in browser |
| `NetworkError` | 4 | Timeout, DNS failure | Check internet connection |
| `ApiError` | 5 | Unexpected response, API changes | Check API compatibility |
| `UserInputError` | 6 | Invalid app selection | Provide valid `--app-id` |
| `HttpStatusError` | 5 | 4xx/5xx responses | Check logs for details |

### Error Message Format

All user-facing errors follow this pattern:
```
{emoji} {descriptive_message}

Details:
- {specific_detail_1}
- {specific_detail_2}
```

Example:
```
❌ HTTP 401 calling https://app.tabidoo.cloud/api/v2/users/me: Unauthorized

Details:
- Token may be expired or invalid
- Re-authenticate in the browser and copy new token to .env
```

---

## Troubleshooting

### Common Issues

#### 1. "Missing TABIDOO_API_TOKEN or TABIDOO_FE_TOKEN"

**Cause**: No usable token found in environment or `.env` file

**Solution**:
```bash
# Create .env file
cat > .env << EOF
TABIDOO_API_TOKEN=your_token_here
EOF
```

#### 2. "HTTP 401 calling /v2/users/me"

**Cause**: Token is invalid or expired

**Solution**:
1. Open Tabidoo in browser
2. Regenerate API token in user settings or log in again if using FE token
3. Update `.env` file

#### 3. "No apps returned for this token"

**Cause**: Token has no app access, or wrong base URL

**Solution**:
- Verify token has access to apps in the web UI
- Try specifying `--base-url` explicitly
- Check if using correct Tabidoo instance

#### 4. "Full schema export was skipped"

**Cause**: `TABIDOO_FE_TOKEN` is missing, invalid, or `/application/getApplicationTypeScriptDefinition` rejected the token

**Solution**:
- Verify `TABIDOO_FE_TOKEN`
- Re-export if you also need `schema.md`
- `tables.md` and `scripts.md` are still considered valid output

#### 5. "Invalid JSON response"

**Cause**: API response format changed, or network corruption

**Solution**:
- Use `--verbose` to inspect responses
- Check if API version is compatible
- Verify network connection stability

---

## Performance Considerations

### Request Optimization

**Per-Table TSD Fetching**: When `TABIDOO_FE_TOKEN` is available, full schema definitions are fetched individually per table. This:
- Provides granular progress updates
- Allows partial success (some tables may fail)
- Mimics browser behavior for better compatibility

**Trade-off**: More HTTP requests = longer execution time for apps with 50+ tables

**Tables Overview Rendering**:
- `tables.md` is built from one app detail payload already loaded for extraction
- No extra per-table schema requests are needed for the navigation document

### Memory Usage

**JSON Parsing**: All API responses are loaded into memory. For large apps (1000+ fields), this can use 100-500 MB of RAM.

**Mitigation**: Python's garbage collection handles cleanup after each processing step.

### Output File Size

**Typical Sizes**:
- Schema file: 50 KB - 20 MB
- Tables file: 10 KB - 500 KB
- Scripts file: 10 KB - 2 MB

**Large Apps** (100+ tables, 1000+ fields):
- Schema file: up to 20 MB
- Tables file: up to 2 MB
- Scripts file: up to 10 MB

---

## Security Best Practices

### Token Handling

**DO**:
- Store token in `.env` file (never commit to git)
- Add `.env` to `.gitignore`
- Use environment variables in CI/CD
- Rotate tokens regularly
- Prefer `TABIDOO_API_TOKEN` for automation; add `TABIDOO_FE_TOKEN` only when full schema export is required

**DON'T**:
- Hardcode tokens in source code
- Print tokens in logs (even in verbose mode)
- Share tokens in plain text
- Commit tokens to version control

### Code Injection

**Risk**: Extracted code from Tabidoo apps may contain malicious JavaScript/TypeScript

**Mitigation**:
- Output files are pure text (Markdown)
- No code is executed during extraction
- Review extracted code before using in production
- Treat output files as untrusted input

---

## Deployment

### Standalone Script

```bash
# Package as standalone executable (PyInstaller)
pip install pyinstaller
pyinstaller --onefile tabidoo_llm_export.py
```

### Docker Container

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY tabidoo_llm_export/ ./tabidoo_llm_export/

# Install dependencies
RUN uv sync --frozen

# Set environment
ENV TABIDOO_API_TOKEN=""
ENV TABIDOO_FE_TOKEN=""

# Entry point
CMD ["uv", "run", "tabidoo-llm-export"]
```

Usage:
```bash
docker build -t tabidoo-exporter .
docker run -v $(pwd)/out:/app/out -e TABIDOO_API_TOKEN=$TOKEN tabidoo-exporter --yes
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Export Tabidoo App

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Export app
        env:
          TABIDOO_API_TOKEN: ${{ secrets.TABIDOO_API_TOKEN }}
          TABIDOO_FE_TOKEN: ${{ secrets.TABIDOO_FE_TOKEN }}
        run: |
          uv sync
          uv run tabidoo-llm-export --app-id ${{ secrets.APP_ID }} --yes

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: exports
          path: out/
```

---

## Future Enhancements

### Planned Features

1. **Multi-App Export**: Export multiple apps in one run
2. **Incremental Updates**: Only fetch changed definitions
3. **Custom Output Formats**: JSON, YAML, plain TypeScript
4. **Filtering**: Exclude specific tables/fields from export
5. **Diff Mode**: Compare exports between versions
6. **Watch Mode**: Auto-export on app changes
7. **Caching**: Cache full schema definitions locally
8. **Selective Exports**: Allow exporting only schema / tables / scripts

### API Compatibility

**Current API Version**: Tested with Tabidoo Cloud (2024-2025)

**Potential Breaking Changes**:
- Endpoint path changes
- JSON response structure changes
- Authentication method changes
- New field types

**Mitigation**: Version pin or API version negotiation

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd tabidoo_llm_scraper

# Install dependencies
uv sync

# Run in development mode
uv run python -m tabidoo_llm_export --help

# Format code (install ruff first)
uv pip install ruff
ruff check .
ruff format .
```

### Pull Request Guidelines

1. **Code Style**: Follow existing patterns, use type hints
2. **Error Handling**: Use appropriate `CliError` subclasses
3. **Constants**: Add new constants to `constants.py`, not inline
4. **Documentation**: Update this file for significant changes
5. **Testing**: Add tests for new features (when test framework exists)

---

## License

(Specify license here)

---

## Contact & Support

**Issues**: Report bugs and feature requests via GitHub Issues

**Questions**: Contact project maintainer

---

## Appendix: JSON Field Reference

### App Structure Fields

```python
# App object
{
  "id": str,                    # App ID
  "name": str,                  # Display name
  "internalName": str,          # URL-safe internal name
  "tables": [...]               # List of table objects
}

# Table object
{
  "id": str,                    # Table ID (schemaId)
  "internalNameApi": str,       # API internal name
  "items": [...],               # List of field objects
  "scripts": [...]              # List of table script objects
}

# Field object
{
  "name": str,                  # Field name
  "type": str,                  # Field type (calculatedfield, buttonform, etc.)
  "metadata": {
    "script": {                 # For calculated fields
      "jsScript": str,
      "tsScript": str
    },
    "freeHtmlInitScript": {     # For free HTML fields
      "jsScript": str,
      "tsScript": str
    }
  }
}

# Table script object
{
  "name": str,                  # Script name
  "jsScript": str,              # JavaScript code
  "tsScript": str               # TypeScript code
}
```

### Workflow Data Fields

```python
# Workflow record
{
  "fields": {
    "name": str,                # Workflow name
    "definition": {
      "triggers": [...],        # Trigger configuration
      "steps": [
        {
          "type": "jsScript",   # Direct script step
          "data": {
            "script": {
              "runableSript": str,         # Note: typo in API (Sript)
              "writtenTypeScript": str
            }
          }
        },
        {
          "type": "foreach",    # Container step; may hide nested workflow code
          "data": {
            "workflowDefinition": {
              "steps": [
                {
                  "type": "jsScript",
                  "data": {
                    "script": {
                      "runableSript": str,
                      "writtenTypeScript": str
                    }
                  }
                }
              ]
            }
          }
        }
      ]
    }
  }
}
```

### Custom Script Data Fields

```python
# Custom script record
{
  "fields": {
    "name": str,                # Script name
    "namespace": str,           # Namespace for organization
    "interface": str,           # Interface definition
    "dts": {                    # TypeScript definitions
      "runableSript": str       # Note: typo in API (Sript)
    },
    "script": {                 # Runnable script
      "runableSript": str       # Note: typo in API (Sript)
    }
  }
}
```

---

*Last Updated: 2026-03-13*
*Version: 0.1.0*
