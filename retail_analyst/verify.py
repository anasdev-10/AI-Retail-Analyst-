import yaml
import sys

try:
    with open('semantic/semantic_model.yml', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    metrics = list(data['metrics'].keys())
    dimensions = list(data['dimensions'].keys())
    joins = list(data['allowed_joins']['fact_sales_line'].keys())
    forbidden = data['safety']['forbidden_keywords']
    
    print('YAML VALID: Yes')
    print(f"Metrics ({len(metrics)}): {metrics}")
    print(f"Dimensions ({len(dimensions)}): {dimensions}")
    print(f"Allowed joins ({len(joins)}): {joins}")
    print(f"Forbidden keywords ({len(forbidden)}): {forbidden}")
    print(f"Default limit: {data['safety']['default_limit']}")
    print(f"Max limit: {data['safety']['max_limit']}")
    print(f"Query timeout: {data['safety']['query_timeout_seconds']}s")
    print(f"allowed_sql_roots: {data['safety']['allowed_sql_roots']}")

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
