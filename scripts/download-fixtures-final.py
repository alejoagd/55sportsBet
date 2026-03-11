#!/usr/bin/env python
"""
Download upcoming fixtures from football-data.org and format for 55sportsBet database.

This version:
- Uses semicolon separator (;)
- Outputs only 3 columns: date;home;away
- Maps API team names to database team names
- Uses d/m/yyyy date format

Usage:
    python scripts/download-fixtures-final.py --leagues all
"""

import os
import sys
import requests
import argparse
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# League mappings: CSV code -> football-data.org competition ID
LEAGUE_MAPPING = {
    'E0': {'id': 2021, 'name': 'Premier League'},
    'SP1': {'id': 2014, 'name': 'La Liga'},
    'D1': {'id': 2002, 'name': 'Bundesliga'},
    'I1': {'id': 2019, 'name': 'Serie A'},
}

# Team name mapping: API name -> Database name
# This maps football-data.org team names to your database names
TEAM_NAME_MAPPING = {
    # Bundesliga (D1) - Based on your database
    'FC Bayern München': 'Bayern Munich',
    'Bayer 04 Leverkusen': 'Leverkusen',
    'Borussia Dortmund': 'Dortmund',
    'RB Leipzig': 'RB Leipzig',
    'TSG 1899 Hoffenheim': 'Hoffenheim',
    'VfL Wolfsburg': 'Wolfsburg',
    'SC Freiburg': 'Freiburg',
    'Eintracht Frankfurt': 'Ein Frankfurt',
    '1. FC Union Berlin': 'Union Berlin',
    'VfB Stuttgart': 'Stuttgart',
    'Borussia Mönchengladbach': "M'gladbach",
    '1. FSV Mainz 05': 'Mainz',
    '1. FC Köln': 'FC Koln',
    'FC Augsburg': 'Augsburg',
    'SV Werder Bremen': 'Werder Bremen',
    'Hamburger SV': 'Hamburg',
    'FC St. Pauli 1910': 'St Pauli',
    '1. FC Heidenheim 1846': 'Heidenheim',

    # Premier League (E0) - Based on your database
    'Manchester City FC': 'Man City',
    'Arsenal FC': 'Arsenal',
    'Liverpool FC': 'Liverpool',
    'Aston Villa FC': 'Aston Villa',
    'Tottenham Hotspur FC': 'Tottenham',
    'Chelsea FC': 'Chelsea',
    'Newcastle United FC': 'Newcastle',
    'Manchester United FC': 'Man United',
    'West Ham United FC': 'West Ham',
    'Brighton & Hove Albion FC': 'Brighton',
    'Wolverhampton Wanderers FC': 'Wolves',
    'Fulham FC': 'Fulham',
    'Everton FC': 'Everton',
    'Brentford FC': 'Brentford',
    'Nottingham Forest FC': "Nott'm Forest",  # Fixed: Nott'ham -> Nott'm
    'Crystal Palace FC': 'Crystal Palace',
    'AFC Bournemouth': 'Bournemouth',
    'Leicester City FC': 'Leicester',
    'Leeds United FC': 'Leeds',
    'Southampton FC': 'Southampton',
    'Ipswich Town FC': 'Ipswich',
    'Burnley FC': 'Burnley',
    'Sunderland AFC': 'Sunderland',
    'Luton Town FC': 'Luton',

    # La Liga (SP1) - Based on your database
    'Real Madrid CF': 'Real Madrid',
    'FC Barcelona': 'Barcelona',
    'Atlético de Madrid': 'Ath Madrid',
    'Club Atlético de Madrid': 'Ath Madrid',  # Alternative name for Atletico
    'Athletic Club': 'Ath Bilbao',
    'Real Sociedad de Fútbol': 'Sociedad',
    'Real Betis Balompié': 'Betis',
    'Villarreal CF': 'Villarreal',
    'Valencia CF': 'Valencia',
    'CA Osasuna': 'Osasuna',
    'Sevilla FC': 'Sevilla',
    'Getafe CF': 'Getafe',
    'Rayo Vallecano de Madrid': 'Vallecano',
    'RC Celta de Vigo': 'Celta',
    'Deportivo Alavés': 'Alaves',
    'RCD Mallorca': 'Mallorca',
    'Girona FC': 'Girona',
    'UD Las Palmas': 'Las Palmas',
    'RCD Espanyol de Barcelona': 'Espanol',
    'Granada CF': 'Granada',
    'Cádiz CF': 'Cadiz',
    'Elche CF': 'Elche',
    'Real Valladolid CF': 'Valladolid',
    'Deportivo Leganés': 'Leganes',
    'UD Almería': 'Almeria',
    'Levante UD': 'Levante',
    'Real Oviedo': 'Oviedo',
    'SD Eibar': 'Eibar',

    # Serie A (I1) - Based on your database
    'SSC Napoli': 'Napoli',
    'FC Internazionale Milano': 'Inter',
    'Juventus FC': 'Juventus',
    'AC Milan': 'Milan',
    'Atalanta BC': 'Atalanta',
    'AS Roma': 'Roma',
    'SS Lazio': 'Lazio',
    'ACF Fiorentina': 'Fiorentina',
    'Torino FC': 'Torino',
    'Bologna FC 1909': 'Bologna',
    'Udinese Calcio': 'Udinese',
    'Hellas Verona FC': 'Verona',
    'Empoli FC': 'Empoli',
    'US Salernitana 1919': 'Salernitana',
    'Monza': 'Monza',
    'US Lecce': 'Lecce',
    'Cagliari Calcio': 'Cagliari',
    'Genoa CFC': 'Genoa',
    'Frosinone Calcio': 'Frosinone',
    'US Sassuolo Calcio': 'Sassuolo',
    'Spezia Calcio': 'Spezia',
    'Parma Calcio 1913': 'Parma',
    'Como 1907': 'Como',
    'Venezia FC': 'Venezia',
    'AC Pisa 1909': 'Pisa',  # Added from your database
    'US Cremonese': 'Cremonese',  # Added from your database
}

API_BASE_URL = "https://api.football-data.org/v4"


def normalize_team_name(api_team_name: str) -> str:
    """
    Convert API team name to database team name.
    If no mapping exists, return the API name as-is (will need manual mapping).
    """
    mapped_name = TEAM_NAME_MAPPING.get(api_team_name)

    if not mapped_name:
        # No mapping found - print warning
        print(f"   ⚠️  No mapping for team: '{api_team_name}' - using API name")
        return api_team_name

    return mapped_name


def get_upcoming_fixtures(api_key: str, competition_id: int) -> List[Dict]:
    """Fetch upcoming fixtures from football-data.org"""
    headers = {
        'X-Auth-Token': api_key
    }

    url = f"{API_BASE_URL}/competitions/{competition_id}/matches"
    params = {
        'status': 'SCHEDULED'
    }

    print(f"   🔗 Fetching from: {url}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        print(f"   📡 Response status: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        matches = data.get('matches', [])
        print(f"   ✅ Found {len(matches)} upcoming fixtures")
        return matches

    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Cannot reach football-data.org")
        print(f"   💡 Check your internet connection")
        return []

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        if e.response.status_code == 429:
            print(f"   ⚠️  Rate limit exceeded. Free tier: 10 requests/minute")
        elif e.response.status_code == 403:
            print(f"   ⚠️  Invalid API key or restricted competition")
            print(f"   💡 Note: Some competitions require paid plan")
        return []

    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {str(e)[:100]}")
        return []


def convert_to_database_format(matches: List[Dict]) -> List[Dict]:
    """
    Convert football-data.org format to YOUR database format:
    date;home;away
    """
    csv_rows = []

    for match in matches:
        # Parse date
        utc_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))

        # Extract team names from API
        home_team_api = match['homeTeam']['name']
        away_team_api = match['awayTeam']['name']

        # Map to database names
        home_team_db = normalize_team_name(home_team_api)
        away_team_db = normalize_team_name(away_team_api)

        # Create CSV row matching YOUR format
        row = {
            'date': utc_date.strftime('%-d/%m/%Y' if os.name != 'nt' else '%#d/%m/%Y'),  # No leading zero: 4/03/2026
            'home': home_team_db,
            'away': away_team_db
        }

        csv_rows.append(row)

    return csv_rows


def save_fixtures_csv(fixtures_data: List[Dict], league_code: str, output_dir: Path) -> bool:
    """Save fixtures to CSV file with YOUR format (semicolon separator)"""
    if not fixtures_data:
        print(f"   ⚠️  No fixtures to save")
        return False

    output_path = output_dir / f"fixtures_{league_code}.csv"

    try:
        # Use semicolon delimiter to match YOUR database format
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'home', 'away'], delimiter=';')
            writer.writeheader()
            writer.writerows(fixtures_data)

        print(f"   ✅ Saved to {output_path}")
        print(f"   📊 Fixtures: {len(fixtures_data)}")

        # Show first few rows as preview
        print(f"   👀 Preview:")
        for i, row in enumerate(fixtures_data[:3], 1):
            print(f"      {i}. {row['date']};{row['home']};{row['away']}")
        if len(fixtures_data) > 3:
            print(f"      ... and {len(fixtures_data) - 3} more")

        return True

    except Exception as e:
        print(f"   ❌ Error saving CSV: {e}")
        return False


def download_fixtures(league_code: str, api_key: str, output_dir: Path) -> bool:
    """Download and save fixtures for a specific league"""
    league_info = LEAGUE_MAPPING.get(league_code)
    if not league_info:
        print(f"   ❌ Unknown league code: {league_code}")
        return False

    print(f"📥 Downloading {league_info['name']} fixtures...")
    print(f"   Competition ID: {league_info['id']}")

    # Fetch from API
    matches = get_upcoming_fixtures(api_key, league_info['id'])

    if not matches:
        return False

    # Convert to YOUR database format
    csv_data = convert_to_database_format(matches)

    # Save to CSV
    return save_fixtures_csv(csv_data, league_code, output_dir)


def test_api_connection(api_key: str) -> bool:
    """Test if API key is valid"""
    print("🔍 Testing API connection...")

    headers = {
        'X-Auth-Token': api_key
    }

    try:
        url = f"{API_BASE_URL}/competitions/2021/matches"  # Test with Premier League
        params = {'limit': 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"   Status code: {response.status_code}")

        if response.status_code == 200:
            print(f"   ✅ API key is valid!")
            return True
        elif response.status_code == 403:
            print(f"   ❌ Invalid API key")
            return False
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Connection test failed: {str(e)[:100]}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Download fixtures for 55sportsBet database')
    parser.add_argument('--output', default='data', help='Output directory')
    parser.add_argument('--leagues', default='all', help='Comma-separated league codes or "all"')
    parser.add_argument('--api-key', help='football-data.org API key (or set FOOTBALL_DATA_ORG_KEY env var)')
    parser.add_argument('--test', action='store_true', help='Test API connection and exit')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('FOOTBALL_DATA_ORG_KEY')
    if not api_key:
        print("❌ API key required!")
        print("\nOptions:")
        print("  1. Pass via command: --api-key YOUR_KEY")
        print("  2. Set environment variable: FOOTBALL_DATA_ORG_KEY")
        print("  3. Add to .env file: FOOTBALL_DATA_ORG_KEY=your_key_here")
        print("\nGet FREE API key at: https://www.football-data.org/client/register")
        sys.exit(1)

    # Test mode
    if args.test:
        print(f"\n{'='*70}")
        print(f"  API CONNECTION TEST")
        print(f"{'='*70}\n")
        success = test_api_connection(api_key)
        sys.exit(0 if success else 1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which leagues to download
    if args.leagues.lower() == 'all':
        leagues_to_download = list(LEAGUE_MAPPING.keys())
    else:
        leagues_to_download = [code.strip().upper() for code in args.leagues.split(',')]

    print(f"\n{'='*70}")
    print(f"  DOWNLOADING UPCOMING FIXTURES")
    print(f"{'='*70}")
    print(f"Source: football-data.org API (FREE)")
    print(f"Output: {output_dir}")
    print(f"Leagues: {', '.join(leagues_to_download)}")
    print(f"Format: date;home;away (semicolon separator)")
    print(f"{'='*70}\n")

    # Download each league
    success_count = 0
    failed_leagues = []

    for league_code in leagues_to_download:
        if download_fixtures(league_code, api_key, output_dir):
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
        print(f"\n💡 Note: Some leagues may require paid plan")
        sys.exit(1)
    else:
        print(f"🎉 All fixtures downloaded successfully!")
        print(f"\n📁 Files created in {output_dir}/:")
        for league in leagues_to_download:
            if league not in failed_leagues:
                print(f"   - fixtures_{league}.csv")
        sys.exit(0)


if __name__ == "__main__":
    main()
