import os
import yaml
import json
import csv
from datetime import datetime
#from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
from server.hf_client import chat_completion

# Import our custom modules
from server.db_connector import DatabaseConnector
from server.sql_validator import SQLValidator, SQLValidationError
from server.prompts import (
    get_analyst_system_prompt,
    get_sql_generation_prompt,
    get_sql_review_prompt,
    get_result_explanation_prompt,
    get_visualization_prompt
)

# Load environment variables
load_dotenv()

# Initialize FastMCP Server
mcp = FastMCP("Retail Analyst Data Server")

# Initialize Database Connector
db = DatabaseConnector()

# Load Semantic Model
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up from server/ to retail_analyst/
SEMANTIC_MODEL_PATH = os.path.join(script_dir, "semantic", "semantic_model.yml")
with open(SEMANTIC_MODEL_PATH, "r", encoding="utf-8") as f:
    semantic_model_data = yaml.safe_load(f)
    semantic_model_text = yaml.dump(semantic_model_data)

# Initialize SQL Validator
sql_validator = SQLValidator(semantic_model_data)

LLM_MODEL = "HuggingFaceH4/zephyr-7b-beta"


# =============================================================================
# === RESOURCES ===
# =============================================================================

@mcp.resource("schema://retail_dw")
def get_schema() -> str:
    """Resource returning the complete retail_dw database schema."""
    return db.get_schema_info()

@mcp.resource("semantic://retail_dw/semantic_model.yml")
def get_semantic_model() -> str:
    """Resource returning the semantic layer definitions."""
    return semantic_model_text


# =============================================================================
# === TOOLS ===
# =============================================================================

@mcp.tool()
def profile_table(table_name: str) -> str:
    """
    Profiles a specific table, returning column names and a sample of 3 rows.
    Only allows tables defined in the semantic model.
    """
    # Allow-list validation
    allowed_tables = set()
    for dim in semantic_model_data.get("dimensions", {}).values():
        allowed_tables.add(dim.get("table"))
    allowed_tables.add(semantic_model_data.get("primary_fact"))
    # Add other known facts
    allowed_tables.update(["fact_returns", "fact_inventory_daily_snapshot"])
    
    if table_name not in allowed_tables:
        return f"Error: Table '{table_name}' is not in the allow-list."
    
    try:
        # Safe to interpolate since it's validated against the allow-list
        query = f"SELECT * FROM retail_dw.{table_name} LIMIT 3;"
        results = db.run_query(query)
        if not results:
            return f"Table {table_name} is empty."
        
        columns = list(results[0].keys())
        return f"Columns: {columns}\nSample Data:\n" + json.dumps(results, default=str, indent=2)
    except Exception as e:
        return f"Error profiling table: {str(e)}"

@mcp.tool()
def audit_tool_call(tool_name: str, parameters: str, status: str, error_msg: str = "") -> str:
    """
    Logs an audit record to a CSV file.
    """
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/audit_log.csv"
    file_exists = os.path.isfile(log_file)
    
    try:
        with open(log_file, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["Timestamp", "Tool", "Parameters", "Status", "ErrorMessage"])
            writer.writerow([datetime.now().isoformat(), tool_name, parameters, status, error_msg])
        return "Audit log recorded successfully."
    except Exception as e:
        return f"Failed to record audit log: {str(e)}"

@mcp.tool()
def validate_sql(sql: str) -> str:
    """
    Validates a SQL query for safety (read-only, no PII, single statement, limits).
    Returns the sanitized SQL if valid, or an error message if invalid.
    """
    try:
        sanitized = sql_validator.validate_and_sanitize(sql)
        return json.dumps({"valid": True, "sanitized_sql": sanitized})
    except SQLValidationError as e:
        audit_tool_call("validate_sql", sql, "FAILED", str(e))
        return json.dumps({"valid": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"valid": False, "error": f"Unexpected error: {str(e)}"})

@mcp.tool()
def run_readonly_query(sql: str) -> str:
    """
    Executes a read-only query against the database. Automatically validates
    the SQL first. Handles timeouts and limits.
    """
    # 1. Validate first
    val_res = json.loads(validate_sql(sql))
    if not val_res["valid"]:
        return f"Query validation failed: {val_res['error']}"
    
    safe_sql = val_res["sanitized_sql"]
    
    # 2. Execute
    try:
        results = db.run_query(safe_sql)
        audit_tool_call("run_readonly_query", safe_sql, "SUCCESS")
        return json.dumps({
            "status": "success",
            "row_count": len(results),
            "data": results
        }, default=str)
    except Exception as e:
        audit_tool_call("run_readonly_query", safe_sql, "FAILED", str(e))
        return json.dumps({
            "status": "error",
            "error": str(e)
        })

@mcp.tool()
def generate_sql(question: str) -> str:
    """
    Calls the LLM to generate a SQL query based on the business question,
    schema, and semantic model.
    """
    schema_info = db.get_schema_info()
    prompt = get_sql_generation_prompt(question, schema_info, semantic_model_text)
    system = get_analyst_system_prompt()
    
    try:
        raw_sql = chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            model_id=LLM_MODEL,
            max_new_tokens=1024,
            temperature=0.1,
        )
        
        # Clean up any markdown blocks if Gemini adds them
        if raw_sql.startswith("```sql"):
            raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
        elif raw_sql.startswith("```"):
            raw_sql = raw_sql.replace("```", "").strip()
        
        # Second-opinion check via SQL review prompt
        review_prompt = get_sql_review_prompt(raw_sql)
        review_result = chat_completion(
            [{"role": "user", "content": review_prompt}],
            model_id=LLM_MODEL,
            max_new_tokens=200,
            temperature=0.1,
        )
        if not review_result.startswith("APPROVED"):
            audit_tool_call("generate_sql", question, "REJECTED_BY_REVIEWER", review_result)
            return json.dumps({"status": "error", "error": f"Reviewer rejected query: {review_result}"})
            
        return json.dumps({"status": "success", "sql": raw_sql})
        
    except Exception as e:
        audit_tool_call("generate_sql", question, "FAILED", str(e))
        return json.dumps({"status": "error", "error": str(e)})

@mcp.tool()
def explain_result(question: str, query_result_json: str) -> str:
    """
    Explains the query results in plain business language using the LLM.
    """
    try:
        data = json.loads(query_result_json)
        if "data" not in data or not data["data"]:
            return "No data was returned to explain."
            
        rows_dicts = data["data"]
        columns = list(rows_dicts[0].keys())
        rows = [[row[col] for col in columns] for row in rows_dicts]
        
        prompt = get_result_explanation_prompt(question, columns, rows)
        system = get_analyst_system_prompt()
        
        full_prompt = f"{system}\n\n{prompt}"
        return chat_completion(
            [
                {"role": "system", "content": get_analyst_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            model_id=LLM_MODEL,
            max_new_tokens=1024,
            temperature=0.3,
        )
        
    except Exception as e:
        return f"Error explaining result: {str(e)}"

@mcp.tool()
def suggest_chart(question: str, query_result_json: str) -> str:
    """
    Asks the LLM to recommend the best chart type for the given query results.
    Returns a structured JSON object describing the chart.
    """
    try:
        data = json.loads(query_result_json)
        if "data" not in data or not data["data"]:
            return json.dumps({"chart_type": "table", "reason": "No data available."})
            
        rows_dicts = data["data"]
        columns = list(rows_dicts[0].keys())
        rows = [[row[col] for col in columns] for row in rows_dicts]
        
        prompt = get_visualization_prompt(question, columns, rows)
        
        res_text = chat_completion(
            [{"role": "user", "content": prompt}],
            model_id=LLM_MODEL,
            max_new_tokens=500,
            temperature=0.1,
        )
        # Ensure it's purely JSON if wrapped in markdown
        if res_text.startswith("```json"):
            res_text = res_text.replace("```json", "").replace("```", "").strip()
        elif res_text.startswith("```"):
            res_text = res_text.replace("```", "").strip()
        return res_text
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def generate_chart_data(query_result_json: str, chart_config_json: str) -> str:
    """
    Transforms the raw database query results into a format optimized for frontend 
    charting libraries based on the suggested chart configuration.
    """
    try:
        data = json.loads(query_result_json).get("data", [])
        config = json.loads(chart_config_json)
        
        if not data:
            return json.dumps({"error": "No data provided."})
            
        chart_type = config.get("chart_type", "table")
        x_col = config.get("x_axis")
        y_col = config.get("y_axis")
        
        result = {
            "chart_type": chart_type,
            "title": config.get("title", "Data Visualization"),
            "labels": [],
            "values": []
        }
        
        if chart_type in ["bar", "line", "pie"] and x_col and y_col:
            result["labels"] = [row.get(x_col) for row in data]
            result["values"] = [row.get(y_col) for row in data]
            
        elif chart_type == "kpi_card" and y_col:
            result["values"] = [data[0].get(y_col)]
            
        else:
            # Fallback to table format
            result["chart_type"] = "table"
            result["rows"] = data
            
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate chart data: {str(e)}"})


# =============================================================================
# === PROMPTS ===
# =============================================================================

@mcp.prompt()
def clarify_question(ambiguous_question: str) -> str:
    """
    Prompt template used when the system needs to ask the user for clarification.
    """
    return f"""The user asked: "{ambiguous_question}"

This question is ambiguous or lacks necessary context (e.g., missing date range, unclear metric).
Please ask ONE specific, polite clarifying question to the user so we can accurately 
generate the SQL query. Do not attempt to guess their intent."""


# =============================================================================
# === SERVER STARTUP ===
# =============================================================================

if __name__ == "__main__":
    print("Starting Retail Analyst MCP Server...")
    mcp.run()
