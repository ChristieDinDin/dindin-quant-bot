#!/usr/bin/env python3
"""
Download the latest market_data.db from GitHub Releases.

The DB is no longer tracked in git (too large for binary diffs).
Instead it lives as a Release Asset on the public repo and is
downloaded on first run / when refreshing.

Usage:
    python scripts/download_db.py          # download to default path
    python scripts/download_db.py --check  # just print the remote file size
"""
import argparse
import sys
from pathlib import Path

OWNER    = "ChristieDinDin"
REPO     = "dindin-quant-bot"
TAG      = "db-latest"
FILENAME = "market_data.db"
DB_PATH  = Path("data/database/market_data.db")
DOWNLOAD_URL = f"https://github.com/{OWNER}/{REPO}/releases/download/{TAG}/{FILENAME}"


def download(dest: Path = DB_PATH, show_progress: bool = True) -> None:
    try:
        import requests
    except ImportError:
        print("pip install requests  ← needed for download_db.py")
        sys.exit(1)

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    print(f"⬇️  Downloading DB from GitHub Release…")
    print(f"   {DOWNLOAD_URL}")

    with requests.get(DOWNLOAD_URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done  = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                if show_progress and total:
                    bar = "█" * int(done / total * 30)
                    pct = done / total * 100
                    mb  = done / 1024 / 1024
                    print(f"\r   [{bar:<30}] {pct:5.1f}%  {mb:.1f} MB", end="", flush=True)

    print()
    tmp.replace(dest)
    size_mb = dest.stat().st_size / 1024 / 1024
    print(f"✅ Saved to {dest}  ({size_mb:.1f} MB)")


def check() -> None:
    try:
        import requests
    except ImportError:
        print("pip install requests")
        sys.exit(1)
    r = requests.head(DOWNLOAD_URL, allow_redirects=True, timeout=10)
    size = int(r.headers.get("content-length", 0))
    print(f"Remote DB size: {size / 1024 / 1024:.1f} MB  ({DOWNLOAD_URL})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Only show remote file size")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        download()
