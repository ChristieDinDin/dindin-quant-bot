#!/usr/bin/env python3
"""
Restore database from GitHub Actions artifacts.

This script helps you download and restore your database backup from GitHub Actions
if your local Mac database gets corrupted or lost.

Usage:
    python scripts/restore_from_github.py --token YOUR_GITHUB_TOKEN

Requirements:
    pip install requests
"""

import os
import sys
import argparse
import requests
import zipfile
import shutil
from datetime import datetime
from pathlib import Path


def get_latest_artifact(repo_owner, repo_name, artifact_name, token):
    """
    Get the latest artifact from GitHub Actions.
    
    Args:
        repo_owner: GitHub username
        repo_name: Repository name
        artifact_name: Name of the artifact (e.g., 'market-database')
        token: GitHub personal access token
    
    Returns:
        Download URL for the artifact
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/artifacts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"🔍 Fetching artifacts from {repo_owner}/{repo_name}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch artifacts: {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    data = response.json()
    artifacts = data.get('artifacts', [])
    
    # Filter for the specific artifact name
    matching = [a for a in artifacts if a['name'] == artifact_name]
    
    if not matching:
        print(f"❌ No artifacts found with name '{artifact_name}'")
        return None
    
    # Sort by created_at to get the latest
    matching.sort(key=lambda x: x['created_at'], reverse=True)
    latest = matching[0]
    
    print(f"✅ Found latest artifact:")
    print(f"   Name: {latest['name']}")
    print(f"   Size: {latest['size_in_bytes'] / 1024 / 1024:.2f} MB")
    print(f"   Created: {latest['created_at']}")
    
    return latest['archive_download_url']


def download_artifact(download_url, output_path, token):
    """
    Download artifact from GitHub.
    
    Args:
        download_url: URL to download from
        output_path: Path to save the downloaded file
        token: GitHub personal access token
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"📥 Downloading artifact...")
    response = requests.get(download_url, headers=headers, stream=True)
    
    if response.status_code != 200:
        print(f"❌ Failed to download: {response.status_code}")
        return False
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Downloaded to {output_path}")
    return True


def extract_and_restore(zip_path, db_path):
    """
    Extract database from zip and restore it.
    
    Args:
        zip_path: Path to the downloaded zip file
        db_path: Path where to restore the database
    """
    # Create backup of existing database
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"💾 Backing up existing database to {backup_path}")
        shutil.copy2(db_path, backup_path)
    
    # Extract
    print(f"📦 Extracting database...")
    temp_dir = Path(zip_path).parent / "temp_extract"
    temp_dir.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find the database file
    db_file = temp_dir / "market_data.db"
    if not db_file.exists():
        print(f"❌ Database file not found in artifact")
        shutil.rmtree(temp_dir)
        return False
    
    # Restore
    print(f"♻️  Restoring database to {db_path}")
    shutil.copy2(db_file, db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)
    os.remove(zip_path)
    
    print(f"✅ Database restored successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Restore database from GitHub Actions artifacts'
    )
    parser.add_argument(
        '--token',
        required=True,
        help='GitHub personal access token (create at https://github.com/settings/tokens)'
    )
    parser.add_argument(
        '--owner',
        default=None,
        help='GitHub username (auto-detected from git if not provided)'
    )
    parser.add_argument(
        '--repo',
        default='DinDin_Quant_Bot',
        help='Repository name (default: DinDin_Quant_Bot)'
    )
    parser.add_argument(
        '--artifact',
        default='market-database',
        help='Artifact name (default: market-database)'
    )
    parser.add_argument(
        '--output',
        default='data/database/market_data.db',
        help='Output path for restored database'
    )
    
    args = parser.parse_args()
    
    # Auto-detect owner from git remote if not provided
    if not args.owner:
        try:
            import subprocess
            remote = subprocess.check_output(
                ['git', 'config', '--get', 'remote.origin.url'],
                text=True
            ).strip()
            # Extract owner from git@github.com:owner/repo.git or https://github.com/owner/repo
            if 'github.com' in remote:
                if remote.startswith('git@'):
                    args.owner = remote.split(':')[1].split('/')[0]
                else:
                    args.owner = remote.split('github.com/')[1].split('/')[0]
                print(f"📌 Auto-detected owner: {args.owner}")
            else:
                print("❌ Could not auto-detect owner from git remote")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Could not auto-detect owner: {e}")
            print("   Please provide --owner manually")
            sys.exit(1)
    
    print("\n" + "="*60)
    print("🔄 GitHub Actions Database Restore")
    print("="*60)
    
    # Get latest artifact
    download_url = get_latest_artifact(
        args.owner,
        args.repo,
        args.artifact,
        args.token
    )
    
    if not download_url:
        sys.exit(1)
    
    # Download
    temp_zip = Path(args.output).parent / f"{args.artifact}.zip"
    if not download_artifact(download_url, temp_zip, args.token):
        sys.exit(1)
    
    # Extract and restore
    if not extract_and_restore(temp_zip, args.output):
        sys.exit(1)
    
    # Verify
    import sqlite3
    conn = sqlite3.connect(args.output)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT symbol) as stocks, COUNT(*) as rows FROM daily_kline")
    stocks, rows = cursor.fetchone()
    conn.close()
    
    print("\n" + "="*60)
    print("📊 Restored Database Stats")
    print("="*60)
    print(f"Stocks: {stocks}")
    print(f"Total rows: {rows:,}")
    print("="*60)
    print("\n✅ Restore complete! Your database is ready to use.")


if __name__ == '__main__':
    main()
