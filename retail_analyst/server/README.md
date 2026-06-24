# =============================================================================
# Member 3: MCP Backend Server
# =============================================================================

This directory contains the FastMCP backend server for the Retail Data Analyst Assistant. It bridges the gap between the natural language LLM and the PostgreSQL `retail_dw` data warehouse securely.

## Components

1. **`mcp_server.py`**: The core FastMCP application exposing tools and resources.
2. **`db_connector.py`**: PostgreSQL database connector using the restricted `mcp_readonly` user.
3. **`sql_validator.py`**: Security module enforcing read-only constraints, limiting row returns, and blocking PII columns.
4. **`prompts.py`**: Contains all Anthropic LLM system and tool prompt templates (managed by Member 2).

## Setup Instructions

### 1. Install Dependencies
You need `mcp` (which includes FastMCP), `psycopg2`, `python-dotenv`, `pyyaml`, and `anthropic`.
```bash
pip install mcp psycopg2-binary python-dotenv pyyaml anthropic
```

### 2. Configure Environment Variables
Create a `.env` file in the `retail_analyst` directory (where `mcp_server.py` is run from):

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=retail_dw_db
DB_USER=mcp_readonly
DB_PASSWORD=mcp_readonly_pass123
DB_TIMEOUT_MS=10000

ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Run the Server
The FastMCP server uses the Standard Input/Output (stdio) transport by default, designed to be connected as a subprocess by an MCP client.

For development or testing the server endpoints, you can use the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python -m server.mcp_server
```

*(Note: Run this from the `retail_analyst` root directory so that it can find `server/` and `semantic/` folders.)*

## Security Features Implemented
- **Read-Only Role**: Connects via `mcp_readonly` which has no DDL/DML permissions.
- **Statement Timeout**: Kills queries taking longer than 10 seconds.
- **Strict SQL Validation**: Rejects queries with forbidden keywords (INSERT, DROP, etc.) or multiple statements.
- **PII Blocking**: Hardcoded blocks against querying `email_hash` and `phone_hash`.
- **Audit Logging**: Every tool execution is logged to `logs/audit_log.csv`.
