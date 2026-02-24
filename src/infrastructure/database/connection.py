"""
Database connection management.

Provides connection pooling and transaction management for SQLite.
Can be extended to support PostgreSQL or other databases in the future.
"""
import sqlite3
from contextlib import contextmanager
from typing import Optional, Generator
from pathlib import Path
import threading


class DatabaseConnection:
    """
    Thread-safe database connection manager.
    
    Features:
    - Connection pooling
    - Transaction management
    - Thread-safe operations
    - Automatic cleanup
    """
    
    def __init__(self, db_path: str, check_same_thread: bool = False):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
            check_same_thread: SQLite thread check (False for multi-threading)
        """
        self.db_path = Path(db_path)
        self.check_same_thread = check_same_thread
        self._local = threading.local()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection for the current thread.
        
        Returns:
            sqlite3.Connection
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=self.check_same_thread
            )
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Return rows as dict-like objects
            self._local.connection.row_factory = sqlite3.Row
        
        return self._local.connection
    
    def close(self) -> None:
        """Close the connection for the current thread."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database transactions.
        
        Usage:
            with db.transaction() as cursor:
                cursor.execute("INSERT INTO ...")
                # Automatically commits on success, rolls back on exception
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for getting a cursor (without transaction).
        
        Usage:
            with db.cursor() as cursor:
                cursor.execute("SELECT ...")
                results = cursor.fetchall()
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a single query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor with results
        """
        conn = self.get_connection()
        return conn.execute(query, params)
    
    def executemany(self, query: str, params_list: list) -> None:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
        """
        with self.transaction() as cursor:
            cursor.executemany(query, params_list)
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and fetch one result."""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute query and fetch all results."""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.fetchone(query, (table_name,))
        return result is not None
    
    def get_tables(self) -> list[str]:
        """Get list of all tables in database."""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table'
            ORDER BY name
        """
        results = self.fetchall(query)
        return [row['name'] for row in results]
    
    def vacuum(self) -> None:
        """Optimize database (VACUUM command)."""
        conn = self.get_connection()
        conn.execute("VACUUM")
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
    
    def __repr__(self) -> str:
        return f"DatabaseConnection(db_path='{self.db_path}')"


# Global database instance
_db_instance: Optional[DatabaseConnection] = None
_db_lock = threading.Lock()


def get_database(db_path: str = "data/database/market_data.db") -> DatabaseConnection:
    """
    Get the global database instance (singleton pattern).
    
    Args:
        db_path: Path to database file
        
    Returns:
        DatabaseConnection instance
    """
    global _db_instance
    
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = DatabaseConnection(db_path)
    
    return _db_instance


def close_database() -> None:
    """Close the global database instance."""
    global _db_instance
    
    if _db_instance:
        _db_instance.close()
        _db_instance = None
