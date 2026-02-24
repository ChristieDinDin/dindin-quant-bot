"""
Initial database schema migration.

Version: 1
Created: 2024-01-01
"""
from ..connection import DatabaseConnection


def upgrade(db: DatabaseConnection) -> None:
    """
    Create initial database schema.
    """
    with db.transaction() as cursor:
        # Create daily_kline table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_kline (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON daily_kline(symbol, date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date 
            ON daily_kline(date)
        ''')
        
        # Create migrations tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Record this migration
        cursor.execute('''
            INSERT OR IGNORE INTO schema_migrations (version)
            VALUES (1)
        ''')


def downgrade(db: DatabaseConnection) -> None:
    """
    Rollback this migration.
    """
    with db.transaction() as cursor:
        cursor.execute('DROP TABLE IF EXISTS daily_kline')
        cursor.execute('DROP INDEX IF EXISTS idx_symbol_date')
        cursor.execute('DROP INDEX IF EXISTS idx_date')
        cursor.execute('DELETE FROM schema_migrations WHERE version = 1')


if __name__ == '__main__':
    # Can be run standalone for testing
    from ..connection import get_database
    
    db = get_database()
    print("Running migration v1_init_schema...")
    upgrade(db)
    print("Migration completed successfully!")
