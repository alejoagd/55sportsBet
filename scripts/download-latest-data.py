#!/usr/bin/env python
"""
Downloads latest CSV data from football-data.co.uk for all leagues.

Usage:
    python scripts/download-latest-data.py
    python scripts/download-latest-data.py --season 2425
"""

import os
import sys
import requests
import argparse
from pathlib import Path

# League mappings
LEAGUES = {
    'E0': 'Premier League',
    'SP1': 'La Liga',
    'D1': 'Bundesliga',
    'I1': 'Serie A',
}

BASE_URL = "https://www.football-data.co.uk/mmz4281"


def download_csv(league_code: str, season: str, output_dir: Path):
    """Download CSV for a specific league and season"""
    url = f"{BASE_URL}/{season}/{league_code}.csv"
    output_path = output_dir / f"{league_code}.csv"

    print(f"📥 Downloading {LEAGUES.get(league_code, league_code)}...")
    print(f"   URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Save to file
        with open(output_path, 'wb') as f:
            f.write(response.content)

        # Count rows
        lines = response.text.strip().split('\n')
        row_count = len(lines) - 1  # Exclude header

        print(f"   ✅ Saved to {output_path}")
        print(f"   📊 Rows: {row_count}")

        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"   ⚠️  Not found (season {season} may not be available yet)")
        else:
            print(f"   ❌ HTTP Error: {e}")
        return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Download latest football data CSVs')
    parser.add_argument('--season', default='2526', help='Season code (e.g., 2526 for 2025/2026)')
    parser.add_argument('--output', default='data/raw', help='Output directory')
    parser.add_argument('--leagues', default='all', help='Comma-separated league codes or "all"')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which leagues to download
    if args.leagues.lower() == 'all':
        leagues_to_download = list(LEAGUES.keys())
    else:
        leagues_to_download = [code.strip() for code in args.leagues.split(',')]

    print(f"\n{'='*70}")
    print(f"  DOWNLOADING FOOTBALL DATA")
    print(f"{'='*70}")
    print(f"Season: {args.season}")
    print(f"Output: {output_dir}")
    print(f"Leagues: {', '.join(leagues_to_download)}")
    print(f"{'='*70}\n")

    # Download each league
    success_count = 0
    failed_leagues = []

    for league_code in leagues_to_download:
        if download_csv(league_code, args.season, output_dir):
            success_count += 1
        else:
            failed_leagues.append(league_code)
        print()

    # Summary
    print(f"{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Downloaded: {success_count}/{len(leagues_to_download)}")

    if failed_leagues:
        print(f"❌ Failed: {', '.join(failed_leagues)}")
        sys.exit(1)
    else:
        print(f"🎉 All files downloaded successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
