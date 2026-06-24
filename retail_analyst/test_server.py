import json
from server.db_connector import DatabaseConnector
from server.sql_validator import SQLValidator, SQLValidationError
import yaml

def test_db():
    print("Testing DB Connector...")
    db = DatabaseConnector()
    schema = db.get_schema_info()
    print("Schema retrieved successfully:")
    print(schema[:200] + "...\n")
    
    # Test read-only query
    res = db.run_query("SELECT COUNT(*) as c FROM retail_dw.dim_store")
    print(f"Store count: {res[0]['c']}\n")

def test_validator():
    print("Testing SQL Validator...")
    with open('semantic/semantic_model.yml', 'r', encoding='utf-8') as f:
        semantic = yaml.safe_load(f)
    validator = SQLValidator(semantic)
    
    queries = [
        ("SELECT * FROM fact_sales_line", True),
        ("SELECT * FROM dim_store;", True),
        ("DROP TABLE fact_sales_line", False),
        ("SELECT email_hash FROM dim_customer", False),
        ("UPDATE dim_store SET store_name = 'Test'", False),
        ("WITH x AS (SELECT 1) SELECT * FROM x", True)
    ]
    
    for q, should_pass in queries:
        try:
            res = validator.validate_and_sanitize(q)
            if should_pass:
                print(f"PASS: {q} -> {res}")
            else:
                print(f"FAIL (Expected reject but passed): {q}")
        except SQLValidationError as e:
            if not should_pass:
                print(f"PASS (Correctly rejected): {q} -> {e}")
            else:
                print(f"FAIL (Expected pass but rejected): {q} -> {e}")

if __name__ == "__main__":
    test_db()
    test_validator()
