import re

class SQLValidationError(Exception):
    """Custom exception for SQL validation failures."""
    pass

class SQLValidator:
    """
    Validates SQL queries to ensure they are safe, read-only, and adhere to
    the rules defined in the semantic model.
    """
    def __init__(self, semantic_model: dict):
        self.safety_rules = semantic_model.get("safety", {})
        self.forbidden_keywords = [
            kw.upper() for kw in self.safety_rules.get("forbidden_keywords", [])
        ]
        self.allowed_roots = [
            root.upper() for root in self.safety_rules.get("allowed_sql_roots", ["SELECT", "WITH"])
        ]
        self.default_limit = self.safety_rules.get("default_limit", 100)
        self.max_limit = self.safety_rules.get("max_limit", 1000)
        self.pii_fields = self.safety_rules.get("pii_restricted_fields", ["email_hash", "phone_hash"])

    def validate_and_sanitize(self, sql: str) -> str:
        """
        Runs all safety checks on the SQL query. If it passes, returns the sanitized
        query (with appropriate LIMIT appended if necessary). If it fails, raises SQLValidationError.
        """
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL query provided.")

        clean_sql = sql.strip()
        # Remove trailing semicolon if present
        if clean_sql.endswith(";"):
            clean_sql = clean_sql[:-1].strip()

        self._check_starts_with_allowed_root(clean_sql)
        self._check_no_comments(clean_sql)
        self._check_no_multiple_statements(clean_sql)
        self._check_no_forbidden_keywords(clean_sql)
        self._check_no_pii_fields(clean_sql)
        
        sanitized_sql = self._enforce_limit(clean_sql)
        return sanitized_sql

    def _check_starts_with_allowed_root(self, sql: str):
        upper_sql = sql.upper()
        if not any(upper_sql.startswith(root) for root in self.allowed_roots):
            raise SQLValidationError(f"Query must start with one of: {', '.join(self.allowed_roots)}")

    def _check_no_comments(self, sql: str):
        if "--" in sql or "/*" in sql:
            raise SQLValidationError("SQL comments are not allowed.")

    def _check_no_multiple_statements(self, sql: str):
        # We already removed a trailing semicolon. Any remaining semicolon means multiple statements.
        if ";" in sql:
            raise SQLValidationError("Multiple SQL statements are not allowed.")

    def _check_no_forbidden_keywords(self, sql: str):
        # Use regex to match whole words only to avoid false positives 
        # (e.g. matching "UPDATE" inside a column name like "last_update_date")
        upper_sql = sql.upper()
        for kw in self.forbidden_keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, upper_sql):
                raise SQLValidationError(f"Forbidden keyword detected: {kw}")

    def _check_no_pii_fields(self, sql: str):
        lower_sql = sql.lower()
        for pii in self.pii_fields:
            if pii.lower() in lower_sql:
                raise SQLValidationError(f"Access to restricted PII field '{pii}' is forbidden.")

    def _enforce_limit(self, sql: str) -> str:
        """
        Ensures the query has a LIMIT clause that respects the max_limit.
        If no LIMIT is found, appends the default_limit.
        """
        # Simple regex to find "LIMIT <number>" at the end of the query
        limit_match = re.search(r'\bLIMIT\s+(\d+)\s*$', sql, re.IGNORECASE)
        
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit > self.max_limit:
                # Replace with max limit
                return sql[:limit_match.start()] + f"LIMIT {self.max_limit}"
            return sql
        else:
            # No limit found, append default
            return f"{sql} LIMIT {self.default_limit}"
