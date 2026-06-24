-- =============================================================================
-- FILE: 03_readonly_role.sql
-- PURPOSE: Creates a PostgreSQL read-only role (mcp_readonly) used exclusively
--          by the MCP server to connect to the retail_dw schema.
--          This role enforces the security boundary: the LLM can never write,
--          alter, or drop any database object.
--
-- SECURITY MODEL:
--   - mcp_readonly can only SELECT from retail_dw tables
--   - All DDL/DML is blocked at the database-role level (defense in depth)
--   - Application-level validation (sql_validator.py) is an additional layer
--
-- RUN ORDER: Must be executed AFTER 01_schema.sql and 02_seed_data.sql
-- USAGE:   psql -U postgres -d retail_dw_db -f 03_readonly_role.sql
-- NOTE:    Replace 'your_strong_password_here' with a real password before running.
-- =============================================================================

-- === SECTION: CREATE READ-ONLY ROLE ===

-- Create the mcp_readonly role with login capability.
-- This is the only role the MCP server application should use.
CREATE ROLE mcp_readonly WITH
    LOGIN
    PASSWORD 'mcp_readonly_pass123'   -- Replace with a strong password in production
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION;

COMMENT ON ROLE mcp_readonly IS
    'Read-only role for the MCP server. May only SELECT from retail_dw tables. '
    'Used by the AI data analyst assistant to safely query the warehouse.';


-- === SECTION: GRANT SCHEMA ACCESS ===

-- Allow mcp_readonly to see objects inside the retail_dw schema
GRANT USAGE ON SCHEMA retail_dw TO mcp_readonly;


-- === SECTION: GRANT SELECT ON ALL EXISTING TABLES ===

-- Grant SELECT on all 9 currently existing tables in retail_dw
GRANT SELECT ON ALL TABLES IN SCHEMA retail_dw TO mcp_readonly;


-- === SECTION: DEFAULT PRIVILEGES FOR FUTURE TABLES ===
-- Ensures that any new tables added to retail_dw in the future
-- are automatically readable by mcp_readonly without re-running this script.

ALTER DEFAULT PRIVILEGES IN SCHEMA retail_dw
    GRANT SELECT ON TABLES TO mcp_readonly;


-- === SECTION: VERIFY ROLE (informational) ===
-- Uncomment to confirm the role was created correctly:
-- SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
-- FROM pg_roles
-- WHERE rolname = 'mcp_readonly';



-- === SECTION: RECOMMENDED SESSION-LEVEL SETTINGS ===
-- The MCP server application (db_connector.py) must set these after connecting:
--
--   SET statement_timeout = '10s';
--   SET search_path TO retail_dw;
--
-- These are NOT set here because ALTER ROLE SET requires superuser in some
-- PostgreSQL configurations. Instead, the application sets them per-session.
--
-- Optional: To enforce timeout at the role level (requires superuser):
--   ALTER ROLE mcp_readonly SET statement_timeout = '10000';  -- 10 seconds in ms
--   ALTER ROLE mcp_readonly SET search_path TO retail_dw;
-- =============================================================================
