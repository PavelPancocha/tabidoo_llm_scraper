# Tabidoo LLM Export CLI - Technical Documentation

## Project Overview

**Tabidoo LLM Export CLI** is a standalone Python command-line tool that exports Tabidoo application context into LLM-ready files. It provides an interactive user experience for downloading TypeScript definitions and application scripts from Tabidoo cloud applications, preparing them for use with Large Language Models.

### Purpose

The tool bridges Tabidoo's low-code platform with AI-assisted development by:
- Extracting TypeScript definitions (`.d.ts`) from Tabidoo applications
- Collecting all custom scripts, workflows, and code blocks
- Formatting the extracted data in a structured Markdown format optimized for LLM consumption
- Providing a clean, interactive CLI experience with rich terminal output

### Key Capabilities

1. **Authentication**: Uses Tabidoo FE JWT tokens for API access
2. **Interactive Selection**: Lists accessible apps and allows user selection
3. **Comprehensive Extraction**: Downloads TypeScript definitions, custom scripts, workflows, and field-level code
4. **LLM-Optimized Output**: Generates structured Markdown files ready for AI assistant consumption
5. **Rich UX**: Progress bars, colored output, and informative statistics

---

## Architecture Overview

### Technology Stack

- **Python**: 3.13+ (3.11+ supported)
- **Package Manager**: `uv` (modern, fast Python package manager)
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
├── api.py               # Tabidoo API client & TSD fetcher
├── http_client.py       # HTTP request handling
├── extractor.py         # Script/code extraction logic
├── formatters.py        # LLM-optimized Markdown formatting
├── output.py            # File writing operations
├── models.py            # Data models (dataclasses)
├── errors.py            # Custom exception hierarchy
├── constants.py         # Constants, enums, text messages
├── env.py               # Environment & config management
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
- Exception handling for `CliError` and `KeyboardInterrupt`
- Delegates execution to `ExportRunner`

**Flow**:
1. Display banner
2. Load `.env` file
3. Read and validate token
4. Normalize base URL
5. Create and run `ExportRunner`
6. Handle errors with appropriate exit codes

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

**Purpose**: Main business logic coordinating the entire export process.

**Class**: `ExportRunner`

**Process Flow**:
1. **Authenticate** - Validate token via `/v2/users/me`
2. **Load Apps** - Get accessible apps via `/v2/apps`
3. **Select App** - Interactive selection or use `--app-id`
4. **Load App Details** - Get full app structure via `/v2/apps/{appId}`
5. **Fetch TypeScript Definitions** - Download `.d.ts` for each table
6. **Fetch Workflows** - Get workflow data from `wascenarios` table
7. **Fetch Custom Scripts** - Get custom scripts from `customScripts` table
8. **Extract Code** - Parse and extract all code fragments
9. **Format for LLM** - Generate structured Markdown
10. **Write Files** - Save to `{app-name}-schema.md` and `{app-name}-scripts.md`

**Progress Tracking**: Uses Rich progress bars with descriptive steps

**Return Value**: Tuple of `(schema_path, scripts_path)`

---

### 3. **api.py** - Tabidoo API Integration

**Classes**:

#### `TabidooApi`
Core API client wrapping HTTP requests.

**Methods**:
- `get_user()` - Validate token and get user info
- `list_apps()` - List accessible applications
- `get_app_full(app_id)` - Get complete app structure with tables/fields
- `get_table_data(app_id, table_internal)` - Get data from system tables (workflows, custom scripts)
- `get_typescript_definition(app_id, language, schema_id, headers)` - Fetch TypeScript definitions

**Key Features**:
- JSON unwrapping (handles `{data: ...}` responses)
- Error handling with typed exceptions
- Optional endpoint support (returns `None` on failure)

#### `TsdFetcher`
Specialized fetcher for TypeScript definitions with browser-like headers.

**Methods**:
- `fetch(app_id, language, app_full, progress, task_id)` - Fetch `.d.ts` for all tables

**Features**:
- Mimics browser requests with proper headers (Origin, Referer, Accept-Language)
- Per-table fetching with progress updates
- Comment injection for table identification
- Fallback to app-level fetch if no tables

**Headers Sent**:
```
Authorization: Bearer {token}
Accept: application/json, text/plain, */*
Accept-Language: {language};q=0.6
Origin: {origin}
Referer: {origin}/app/{appInternal}/schema/{tableInternal}
appinfo: {urlencoded_json}
```

---

### 4. **extractor.py** - Code Extraction

**Class**: `ScriptExtractor`

**Methods**:

#### `extract(app_structure)` → `ExtractedCode`
Extracts code from application structure (tables, fields, scripts).

**Extraction Targets**:
- **Calculated Fields** (`calculatedfield`) - Field-level scripts
- **Button Fields** (`buttonform`) - Button action scripts
- **Free HTML Fields** (`freehtmlinput`) - HTML init scripts
- **Table Scripts** - Schema-level scripts

**Returns**: `ExtractedCode` with:
- `app_id`
- `app_name`
- `fragments[]` - List of `ExtractedCodeFragment`

#### `extract_workflows(workflows)` → `list[ExtractedWorkflowCodeFragment]`
Extracts JavaScript/TypeScript from workflow definitions.

**Data Source**: `/v2/apps/{appId}/tables/wascenarios/data`

**Extracted**:
- Workflow name
- Triggers (JSON)
- JavaScript/TypeScript from `jsScript` steps

#### `extract_custom_scripts(custom_scripts)` → `list[ExtractedCustomScriptCodeFragment]`
Extracts custom scripts from the custom scripts table.

**Data Source**: `/v2/apps/{appId}/tables/customScripts/data`

**Extracted**:
- Script name
- Namespace
- Interface
- TypeScript definitions (`.d.ts`)
- Runnable script code

---

### 5. **formatters.py** - LLM Output Formatting

**Classes**:

#### `LlmFormatter`
Formats extracted code into LLM-friendly Markdown.

**Output Structure**:
```markdown
# Application Code Analysis

**Application ID:** {app_id}
**Application Name:** {app_name}

## Code Block 1
**Table:** {table_name}
**Field:** {field_name}

```typescript
{typescript_code}
```

## Workflow Code

### Workflow 1: {workflow_name}
**Triggers:** {triggers_json}

```typescript
{typescript_code}
```

## Custom Scripts

### Custom Script 1: {script_name}
**Namespace:** {namespace}
**Interface:** {interface}

```typescript
{script_code}
```
```

#### `MarkdownRenderer`
Wraps TypeScript definitions in Markdown code blocks.

**Output**:
```markdown
# TypeScript Definitions

```typescript
{typescript_definitions}
```
```

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
tsd_lines: int
tsd_bytes: int
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

#### Text Messages
- `Text.TITLE`, `Text.DONE`, `Text.AUTHENTICATING`, etc.
- User-facing messages with emoji icons
- Error messages with formatting placeholders

#### API Endpoints
- `Endpoint.USERS_ME` - `/v2/users/me`
- `Endpoint.APPS` - `/v2/apps`
- `Endpoint.APP_DETAIL` - `/v2/apps/{app_id}`
- `Endpoint.TSD` - `/application/getApplicationTypeScriptDefinition`
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
Reads `TABIDOO_FE_TOKEN` from environment.

**Validation**: Raises `InvalidConfigError` if missing or empty.

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
- `info(msg)`, `success(msg)`, `error(msg)` - Colored output
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

**Method**: `write(out_dir, app, tsd, llm_md)` → `(schema_path, scripts_path)`

**Process**:
1. Create output directory (with parents)
2. Sanitize app name for filename
3. Generate filenames:
   - `{sanitized_name}-schema.md`
   - `{sanitized_name}-scripts.md`
4. Write files with UTF-8 encoding

**Output Structure**:
```
./out/
├── my_app-schema.md    # TypeScript definitions
└── my_app-scripts.md   # Application code analysis
```

---

### 13. **stats.py** - Statistics Calculation

**Class**: `StatsBuilder`

**Method**: `build(app_full, extracted, workflows, custom_scripts, tsd, llm_md)` → `ExportStats`

**Computed Metrics**:
- **Tables** - Count from app structure
- **Fields** - Count from app structure
- **Code blocks** - Number of extracted code fragments
- **Workflow scripts** - Number of workflow code fragments
- **Custom scripts** - Number of custom script fragments
- **TSD lines** - Line count in TypeScript definitions
- **TSD bytes** - Byte size of TypeScript definitions
- **LLM lines** - Line count in formatted output
- **LLM bytes** - Byte size of formatted output

---

## API Integration Details

### Authentication

**Method**: Bearer token (JWT) from browser session

**How to Obtain Token**:
1. Open Tabidoo web app in browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Local Storage
4. Find `TABIDOO_FE_TOKEN` key
5. Copy the value

**Token Storage**: Store in `.env` file as `TABIDOO_FE_TOKEN=xxx`

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
    "tables": [
      {
        "id": "table_id",
        "internalNameApi": "table_name",
        "items": [
          {
            "name": "field_name",
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
Fetches TypeScript definitions.

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
- `TABIDOO_FE_TOKEN` - Frontend JWT token from browser session

**Optional** (via CLI flags):
- `--base-url` - API base URL (default: `https://app.tabidoo.cloud/api`)
- `--language` - Language code for API headers (default: `en`)
- `--timeout` - HTTP timeout in seconds (default: `30`)

### .env File Format

```bash
# Tabidoo FE Token from browser localStorage
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
- `{sanitized_app_name}-scripts.md`

**Sanitization Rules**:
- Convert to lowercase
- Replace spaces with underscores
- Remove special characters (keep only `a-z`, `0-9`, `_`, `-`, `.`)
- Strip leading/trailing `._-`

**Examples**:
- "My App" → `my_app-schema.md`
- "CRM System (v2)" → `crm_system_v2-schema.md`

### Schema File (`*-schema.md`)

Contains TypeScript definitions wrapped in Markdown:

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
    └── sample_tsd.ts         # Sample TypeScript definitions
```

**Testing with Real API**:
```bash
# Set up test .env
echo "TABIDOO_FE_TOKEN=your_test_token" > .env.test

# Run with test environment
uv run python -c "
import os
os.environ['TABIDOO_FE_TOKEN'] = 'test_token'
from tabidoo_llm_export.cli import main
main()
"
```

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

#### 1. "Missing TABIDOO_FE_TOKEN"

**Cause**: Token not found in environment or `.env` file

**Solution**:
```bash
# Create .env file
cat > .env << EOF
TABIDOO_FE_TOKEN=your_token_here
EOF
```

#### 2. "HTTP 401 calling /v2/users/me"

**Cause**: Token is invalid or expired

**Solution**:
1. Open Tabidoo in browser
2. Log in again if needed
3. Extract new token from localStorage
4. Update `.env` file

#### 3. "No apps returned for this token"

**Cause**: Token has no app access, or wrong base URL

**Solution**:
- Verify token has access to apps in the web UI
- Try specifying `--base-url` explicitly
- Check if using correct Tabidoo instance

#### 4. "Unable to fetch TypeScript definitions"

**Cause**: App has no tables, or endpoint authorization failed

**Solution**:
- Verify app has at least one table
- Check token permissions
- Try with `--verbose` to see request details

#### 5. "Invalid JSON response"

**Cause**: API response format changed, or network corruption

**Solution**:
- Use `--verbose` to inspect responses
- Check if API version is compatible
- Verify network connection stability

---

## Performance Considerations

### Request Optimization

**Per-Table TSD Fetching**: For apps with many tables, TypeScript definitions are fetched individually per table. This:
- Provides granular progress updates
- Allows partial success (some tables may fail)
- Mimics browser behavior for better compatibility

**Trade-off**: More HTTP requests = longer execution time for apps with 50+ tables

### Memory Usage

**JSON Parsing**: All API responses are loaded into memory. For large apps (1000+ fields), this can use 100-500 MB of RAM.

**Mitigation**: Python's garbage collection handles cleanup after each processing step.

### Output File Size

**Typical Sizes**:
- Schema file: 50 KB - 5 MB
- Scripts file: 10 KB - 2 MB

**Large Apps** (100+ tables, 1000+ fields):
- Schema file: up to 20 MB
- Scripts file: up to 10 MB

---

## Security Best Practices

### Token Handling

**DO**:
- Store token in `.env` file (never commit to git)
- Add `.env` to `.gitignore`
- Use environment variables in CI/CD
- Rotate tokens regularly

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
ENV TABIDOO_FE_TOKEN=""

# Entry point
CMD ["uv", "run", "tabidoo-llm-export"]
```

Usage:
```bash
docker build -t tabidoo-exporter .
docker run -v $(pwd)/out:/app/out -e TABIDOO_FE_TOKEN=$TOKEN tabidoo-exporter --yes
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
7. **API Key Support**: Use API keys instead of FE tokens
8. **Caching**: Cache TypeScript definitions locally

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
          "type": "jsScript",   # Step type
          "data": {
            "script": {
              "runableSript": str,         # Note: typo in API (Sript)
              "writtenTypeScript": str
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

*Last Updated: 2026-01-14*
*Version: 0.1.0*