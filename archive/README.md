# Archive Folder

This folder contains old files from before the architecture migration (Feb 6, 2024).

## Why These Files Were Archived

All functionality from these old files has been migrated to the new clean architecture in the `src/` directory. These files are kept for reference but are no longer used.

## Contents

### `old_scripts/`
Old Python scripts that have been replaced:

| Old File | New Location |
|----------|--------------|
| `backtest_strategy.py` | `src/core/strategies/mfi_hunter.py` |
| `calc_mfi.py` | `src/core/indicators/mfi.py` |
| `dashboard.py` | `src/presentation/dashboard/app.py` |
| `fetch_data.py` | `scripts/fetch_historical_data.py` |
| `import_data.py` | `scripts/migrate_old_data.py` |
| `init_db.py` | `scripts/setup_db.py` |
| `plot_chart.py` | `src/presentation/dashboard/components/charts.py` |
| `plot_signals.py` | `src/presentation/dashboard/components/charts.py` |

### `old_data/`
Historical CSV data files:
- `2337.TW_history.csv` - Can be imported using `scripts/migrate_old_data.py`
- `6944.TW_history.csv` - Can be imported using `scripts/migrate_old_data.py`
- `2337_mfi_calculated.csv` - No longer needed (calculated on-the-fly)
- `6944_mfi_calculated.csv` - No longer needed (calculated on-the-fly)

### `old_outputs/`
Old backtest result visualizations:
- `MfiHunter.html`
- `MfiHunter(buy_level=35,sell_level=85,mfi_period=16).html`

## Can I Delete This?

**Yes**, after you've verified:
1. ✅ New architecture works correctly
2. ✅ Old CSV data has been migrated to the database
3. ✅ You don't need the old backtest results

To completely remove:
```bash
rm -rf archive/
```

## Database Migration

The old `market_data.db` has been moved to `data/database/market_data.db` (the correct location in the new architecture).
