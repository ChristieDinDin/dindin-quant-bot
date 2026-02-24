#!/usr/bin/env python3
"""
Database setup script.

Initialize the database schema and prepare the system.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.database.connection import get_database
from src.infrastructure.database.migrations.v1_init_schema import upgrade
from src.utils.logger import get_logger, Logger
from src.utils.config import get_config

logger = get_logger(__name__)


def main():
    """Initialize database."""
    print("🚀 DinDin Quant Bot - Database Setup")
    print("=" * 50)
    
    # Load config
    config = get_config()
    Logger.configure(config.logging)
    
    logger.info(f"Setting up database at: {config.database.path}")
    
    # Get database connection
    db = get_database(config.database.path)
    
    try:
        # Run migration
        print("\n📦 Running database migrations...")
        upgrade(db)
        
        # Verify
        tables = db.get_tables()
        print(f"\n✅ Database initialized successfully!")
        print(f"📊 Tables created: {', '.join(tables)}")
        
        print("\n" + "=" * 50)
        print("Database is ready for use!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
