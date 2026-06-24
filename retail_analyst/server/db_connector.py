import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConnector:
    """
    Handles secure, read-only connections to the PostgreSQL retail_dw database.
    Enforces the mcp_readonly role and sets a statement timeout to prevent 
    long-running queries.
    """
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.database = os.getenv("DB_NAME", "retail_dw_db")
        self.user = os.getenv("DB_USER", "mcp_readonly")
        self.password = os.getenv("DB_PASSWORD", "mcp_readonly_pass123")
        
        # Enforce timeout from env, default to 10 seconds
        self.timeout_ms = int(os.getenv("DB_TIMEOUT_MS", "10000"))

    @contextmanager
    def get_connection(self):
        """
        Context manager for PostgreSQL connections.
        Ensures the connection is properly closed after use.
        Also sets the search_path to retail_dw and applies a timeout.
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            # Enforce read-only at the session level as an extra safeguard
            conn.set_session(readonly=True, autocommit=True)
            
            with conn.cursor() as cur:
                # Force search_path and statement_timeout
                cur.execute("SET search_path TO retail_dw;")
                cur.execute(f"SET statement_timeout = {self.timeout_ms};")
            
            yield conn
        finally:
            if conn:
                conn.close()

    def run_query(self, query: str, params: tuple = None) -> list:
        """
        Executes a SELECT query and returns the results as a list of dictionaries.
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return []

    def get_schema_info(self) -> str:
        """
        Retrieves formatted schema information (tables and columns) for the retail_dw schema.
        This is passed to the LLM for query generation context.
        """
        query = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'retail_dw'
            ORDER BY table_name, ordinal_position;
        """
        results = self.run_query(query)
        
        schema_dict = {}
        for row in results:
            t_name = row['table_name']
            c_name = row['column_name']
            if t_name not in schema_dict:
                schema_dict[t_name] = []
            schema_dict[t_name].append(c_name)
            
        # Format as: table_name: [col1, col2, ...]
        formatted_lines = []
        for table, cols in schema_dict.items():
            formatted_lines.append(f"{table}: [{', '.join(cols)}]")
            
        return "\n".join(formatted_lines)
