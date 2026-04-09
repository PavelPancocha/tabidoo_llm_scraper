from __future__ import annotations

from enum import IntEnum, StrEnum, auto


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_CONFIG = 2
    AUTH = 3
    NETWORK = 4
    API = 5
    USER_INPUT = 6
    CANCELLED = 130


class HttpStatus(IntEnum):
    UNAUTHORIZED = 401
    FORBIDDEN = 403


class Defaults:
    BASE_URL = "https://app.tabidoo.cloud/api"
    OUT_DIR = "./out"
    LANGUAGE = "en"
    TIMEOUT_SEC = 30
    ACCEPT_LANGUAGE_QUALITY = "0.6"
    TABLE_DATA_PAGE_LIMIT = 1000


class EnvVar(StrEnum):
    API_TOKEN = "TABIDOO_API_TOKEN"


class Encoding(StrEnum):
    UTF8 = "utf-8"


class UrlPart(StrEnum):
    API = "/api"
    API_V2 = "/api/v2"
    V2 = "/v2"
    HTTP = "http://"
    HTTPS = "https://"


class ErrorKey(StrEnum):
    ERRORS = "errors"
    MESSAGE = "message"


class ApiField(StrEnum):
    APPLICATION_ID = "applicationId"
    ONLY_JS_FUNCTIONS = "onlyJsFunctions"
    SCHEMA_ID = "schemaId"


class DefaultName(StrEnum):
    TABLE_SCRIPT = "table_script"
    TABLE = "table"


class EnvDefaults(StrEnum):
    COMMENT = "#"
    ASSIGN = "="
    QUOTE_DOUBLE = "\""
    QUOTE_SINGLE = "'"
    DOTENV = ".env"


class Char(StrEnum):
    SLASH = "/"


class Separator(StrEnum):
    ERROR_JOIN = "; "
    FILE = "-"


class DecodeDefaults(StrEnum):
    ERROR_HANDLER = "replace"


class TextDefaults(StrEnum):
    ELLIPSIS = "..."


class JsonDefaults:
    SEPARATORS = (",", ":")
    EMPTY_ARRAY = "[]"


class Newline(StrEnum):
    LF = "\n"
    DOUBLE = "\n\n"


class Format(StrEnum):
    ACCEPT_LANGUAGE = "{language};q={quality}"
    APP_NAME = "{name} ({internal})"
    OUTPUT_FILE = "{name}{separator}{suffix}"


class Attr(StrEnum):
    STATUS = "status"


class HeaderName(StrEnum):
    AUTHORIZATION = "Authorization"
    ACCEPT = "Accept"
    CONTENT_TYPE = "Content-Type"
    ACCEPT_LANGUAGE = "Accept-Language"
    USER_AGENT = "User-Agent"


class HeaderValue(StrEnum):
    AUTH_SCHEME = "Bearer"
    ACCEPT_JSON = "application/json"
    ACCEPT_FE = "application/json, text/plain, */*"
    CONTENT_JSON = "application/json"
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"


class Endpoint(StrEnum):
    USERS_ME = "/v2/users/me"
    APPS = "/v2/apps"
    APP_DETAIL = "/v2/apps/{app_id}"
    TSD = "/v2/apps/getApplicationTypeScriptDefinition"
    TABLE_DATA = "/v2/apps/{app_id}/tables/{table}/data"


class TableInternal(StrEnum):
    WORKFLOWS = "wascenarios"
    CUSTOM_SCRIPTS = "customScripts"


class FieldType(StrEnum):
    CALCULATED = "calculatedfield"
    BUTTON = "buttonform"
    FREE_HTML = "freehtmlinput"


class WorkflowStepType(StrEnum):
    JS_SCRIPT = "jsScript"


class JsonKey(StrEnum):
    DATA = "data"
    ID = "id"
    EMAIL = "email"
    NAME = "name"
    SHORT_ID = "shortId"
    INTERNAL_NAME = "internalName"
    INTERNAL_NAME_API = "internalNameApi"
    MODULES = "modules"
    TABLE_IDS = "tableIds"
    TABLES = "tables"
    ITEMS = "items"
    TYPE = "type"
    METADATA = "metadata"
    DESCRIPTION = "description"
    REQUIRED = "required"
    SCRIPT = "script"
    JS_SCRIPT = "jsScript"
    TS_SCRIPT = "tsScript"
    FREE_HTML_INIT_SCRIPT = "freeHtmlInitScript"
    SCRIPTS = "scripts"
    FIELDS = "fields"
    DEFINITION = "definition"
    STEPS = "steps"
    TRIGGERS = "triggers"
    RUNABLE_SCRIPT = "runableSript"
    WRITTEN_TYPESCRIPT = "writtenTypeScript"
    DTS = "dts"
    NAMESPACE = "namespace"
    INTERFACE = "interface"
    HEADER = "header"
    CONTENT = "content"


class OutputSuffix(StrEnum):
    SCHEMA = "schema.md"
    TABLES = "tables.md"
    SCRIPTS = "scripts.md"


class MarkdownText(StrEnum):
    TITLE_TSD = "# TypeScript Definitions"
    CODE_FENCE_TS = "```typescript"
    CODE_FENCE_JS = "```javascript"
    CODE_FENCE_END = "```"
    TITLE_TABLES = "# Application Tables"
    TITLE_ANALYSIS = "# Application Code Analysis"
    TITLE_WORKFLOW = "## Workflow Code"
    TITLE_CUSTOM = "## Custom Scripts"
    BLOCK_PREFIX = "## Code Block {index}"
    WORKFLOW_PREFIX = "### Workflow {index}: {name}"
    CUSTOM_PREFIX = "### Custom Script {index}: {name}"
    MODULE_PREFIX = "## Module: {name}"
    UNGROUPED_TABLES = "## Ungrouped Tables"
    TABLE_PREFIX = "### Table: {name}"
    TABLE_LABEL = "**Table:** {name}"
    FIELD_LABEL = "**Field:** {name}"
    APP_ID_LABEL = "**Application ID:** {value}"
    APP_NAME_LABEL = "**Application Name:** {value}"
    APP_INTERNAL_LABEL = "**Application Internal Name:** {value}"
    TABLE_ID_LABEL = "**Table ID:** {value}"
    TABLE_INTERNAL_LABEL = "**Table Internal Name:** {value}"
    TABLE_FIELDS_HEADER = "| Field Label | Internal Name | Type | Required | Description |"
    TABLE_FIELDS_SEPARATOR = "| --- | --- | --- | --- | --- |"
    TABLE_FIELD_ROW = "| {header} | `{name}` | `{type}` | {required} | {description} |"
    TRIGGERS_LABEL = "**Triggers:** {value}"
    NAMESPACE_LABEL = "**Namespace:** {value}"
    INTERFACE_LABEL = "**Interface:** {value}"
    DEFINITIONS_LABEL = "**Definitions:**"
    SCRIPT_LABEL = "**Script:**"
    TABLE_COMMENT = "// Table: {name} ({schema_id})"


class RegexPattern(StrEnum):
    WHITESPACE = r"\s+"
    INVALID = r"[^a-z0-9_\-\.]+"


class SanitizeDefaults(StrEnum):
    UNDERSCORE = "_"
    EMPTY = ""
    STRIP = "._-"
    FALLBACK = "app"


class BytesDefaults:
    EMPTY = b""


class CollectionDefaults:
    EMPTY = ()


class CliOption:
    APP_ID = ("--app-id",)
    OUT_DIR = ("--out-dir",)
    BASE_URL = ("--base-url",)
    LANGUAGE = ("--language",)
    NO_INTERACTIVE = ("--no-interactive", "--yes")
    TIMEOUT = ("--timeout",)
    VERBOSE = ("--verbose",)


class UiDefaults(IntEnum):
    PROGRESS_BAR_WIDTH = 28
    PROGRESS_UNIT = 1
    INDEX_START = 1


class Limits(IntEnum):
    ERROR_BODY_WIDTH = 800


class CountDefaults(IntEnum):
    ZERO = 0
    ONE = 1


class ProgressStep(IntEnum):
    SCHEMA = auto()
    TABLES = auto()
    WORKFLOWS = auto()
    CUSTOM = auto()
    EXTRACT = auto()
    WRITE = auto()


class TableHeader(StrEnum):
    INDEX = "#"
    NAME = "Name"
    INTERNAL = "Internal"
    ID = "ID"
    METRIC = "Metric"
    VALUE = "Value"


class ProgressText(StrEnum):
    TASK = "{task.description}"
    FRACTION = "{task.completed}/{task.total}"


class Align(StrEnum):
    RIGHT = "right"


class Prefix(StrEnum):
    BULLET = "- "


class SpinnerName(StrEnum):
    DEFAULT = "dots"


class Text(StrEnum):
    TITLE = "✨ Tabidoo LLM Export"
    EXPORTING = "🚀 Exporting"
    USING_INSTANCE = "🌍 Using instance: {base_url}"
    AUTHENTICATED_AS = "👤 Authenticated as: {email}"
    AUTHENTICATING = "🔐 Authenticating"
    LOADING_APPS = "📦 Loading apps"
    LOADING_APP = "🧱 Loading app structure"
    FETCHING_TSD = "🧠 Fetching full schema definitions"
    BUILDING_TABLES = "🗂️ Building tables overview"
    FETCHING_WORKFLOWS = "⚙️ Fetching workflows"
    FETCHING_CUSTOM = "🧩 Fetching custom scripts"
    EXTRACTING = "🧪 Extracting scripts"
    WRITING = "💾 Writing output files"
    DONE = "✅ Export complete"
    AVAILABLE_APPS = "Available apps"
    SELECT_APP = "Select app (number or app id)"
    INVALID_SELECTION = "Invalid selection. Try again."
    NO_APPS = "No apps returned for this token."
    MISSING_TOKEN = "Missing TABIDOO_API_TOKEN. Put it into .env in your working directory."
    BAD_BASE_URL = "Base URL must start with http:// or https://"
    EMPTY_BASE_URL = "Base URL is empty."
    MISSING_APP_ID = "Selected app is missing 'id'."
    APP_ID_NOT_FOUND = "--app-id {app_id} not found among accessible apps."
    MULTI_APP_NEED_ID = "Multiple apps available; provide --app-id (or run without --no-interactive)."
    HTTP_ERROR = "HTTP {status} calling {url}: {message}"
    HTTP_EMPTY = "HTTP {status} calling {url} (empty error body)"
    JSON_ERROR_GET = "Invalid JSON response from GET {path}"
    JSON_ERROR_POST = "Invalid JSON response from POST {path}"
    TSD_MISSING = "Unexpected TypeScript definition response (missing 'content')."
    TSD_FAILED = "Unable to fetch TypeScript definitions for app or any table."
    SKIP_SCHEMA_ERROR = "Skipping full schema export: {reason}"
    CANCELLED = "Cancelled."
    STATS_TITLE = "Export Stats"
    WROTE = "Wrote"
    APPS_SHAPE = "Unexpected /v2/apps response shape (expected list)."
    APP_SHAPE = "Unexpected /v2/apps/{id} response shape (expected object)."
    NETWORK_ERROR = "Network error calling {url}: {detail}"


class Style(StrEnum):
    INFO = "cyan"
    SUCCESS = "bold green"
    WARNING = "yellow"
    ERROR = "bold red"


class StatsLabel(StrEnum):
    TABLES = "Tables"
    FIELDS = "Fields"
    CODE_BLOCKS = "Code blocks"
    WORKFLOWS = "Workflow scripts"
    CUSTOM_SCRIPTS = "Custom scripts"
    SCHEMA_LINES = "Schema lines"
    SCHEMA_BYTES = "Schema bytes"
    TABLES_MD_LINES = "Tables MD lines"
    TABLES_MD_BYTES = "Tables MD bytes"
    LLM_LINES = "LLM lines"
    LLM_BYTES = "LLM bytes"


class HelpText(StrEnum):
    APP_ID = "Select app by id (skips interactive selection)."
    OUT_DIR = "Output directory root."
    BASE_URL = "Tabidoo API base URL."
    LANGUAGE = "Language for request headers."
    NO_INTERACTIVE = "Do not prompt."
    TIMEOUT = "HTTP timeout seconds."
    VERBOSE = "Print request URLs (no secrets)."


class EntryPoint(StrEnum):
    MAIN = "__main__"
