#!/usr/bin/env python3
"""
Migration script to import data from old CSV files to new database.

This helps transition from the old flat structure to the new architecture.
"""
import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository
from src.utils.logger import get_logger, Logger
from src.utils.config import get_config

logger = get_logger(__name__)


def migrate_csv_file(filepath: str, symbol: str, repository: MarketDataRepository) -> int:
    """
    Migrate a single CSV file to database.
    
    Args:
        filepath: Path to CSV file
        symbol: Stock symbol (e.g., '2337.TW')
        repository: MarketDataRepository instance
        
    Returns:
        Number of rows imported
    """
    try:
        # Read CSV
        df = pd.read_csv(filepath, index_col=0, parse_dates=True, header=[0, 1])
        
        # Clean multi-level headers (from yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Standardize column names
        df.columns = [col.capitalize() for col in df.columns]
        
        # Convert to numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove NaN
        df = df.dropna()
        
        # Save to database
        rows = repository.save_dataframe(df, symbol)
        
        return rows
        
    except Exception as e:
        logger.error(f"Failed to migrate {filepath}: {e}")
        return 0


def main():
    """Migrate old CSV data."""
    print("🔄 DinDin Quant Bot - Data Migration")
    print("=" * 50)
    
    # Load config
    config = get_config()
    Logger.configure(config.logging)
    
    # Initialize database
    db = get_database(config.database.path)
    repository = MarketDataRepository(db)
    
    # List of old CSV files to migrate (from archive folder)
    migrations = [
        ('archive/old_data/2337.TW_history.csv', '2337.TW'),
        ('archive/old_data/6944.TW_history.csv', '6944.TW'),
    ]
    
    print("\n📦 Starting migration...\n")
    
    total_rows = 0
    successful = 0
    
    for filepath, symbol in migrations:
        file_path = Path(filepath)
        
        if not file_path.exists():
            print(f"⚠️  {filepath} not found, skipping")
            continue
        
        print(f"Migrating {filepath} as {symbol}...")
        
        rows = migrate_csv_file(str(file_path), symbol, repository)
        
        if rows > 0:
            print(f"  ✓ Imported {rows} rows")
            total_rows += rows
            successful += 1
        else:
            print(f"  ✗ Failed to import")
    
    print("\n" + "=" * 50)
    print(f"✅ Migration complete!")
    print(f"  Files processed: {successful}/{len(migrations)}")
    print(f"  Total rows imported: {total_rows}")
    print("=" * 50)


if __name__ == '__main__':
    main()
