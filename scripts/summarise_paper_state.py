#!/usr/bin/env python3
"""Print a one-line paper trading summary for GitHub Actions step summary."""
import json, pathlib, sys

p = pathlib.Path("data/paper_trading/state.json")
if not p.exists():
    sys.exit(0)

s = json.loads(p.read_text())
summary = s.get("last_scan_summary", {})
entries = len(summary.get("new_entries", []))
exits   = len(summary.get("auto_exits", []))
print(
    f"**Paper Trading:** open={len(s['open_positions'])}, "
    f"closed={len(s['closed_trades'])}, "
    f"new_entries={entries}, auto_exits={exits}, "
    f"cash={s['cash']:.0f} TWD"
)
