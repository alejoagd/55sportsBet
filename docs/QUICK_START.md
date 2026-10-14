# Quick Start Guide - 55sportsBet Automation

## Overview

Automated system for downloading football data, updating results, and generating predictions.

## Data Sources

| Type | Source | Purpose |
|------|--------|---------|
| **Historical Results** | football-data.co.uk | Completed matches with odds |
| **Upcoming Fixtures** | API-Football | Future matches to predict |

## Local Execution (Windows)

### Initial Setup

```bash
# 1. Create virtual environment and install dependencies
setup.bat

# 2. Configure your .env file
# Add database credentials and API key:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
API_FOOTBALL_KEY=your_api_football_key
```

### Regular Updates

```bash
# Option 1: Update everything (recommended)
update-local.bat
# Downloads results, updates database, generates predictions

# Option 2: Update fixtures only
update-fixtures.bat
# Downloads upcoming matches from API-Football

# Option 3: Manual control
python src/scripts/run_update_automated.py --mode complete --leagues all
```

## GitHub Actions (Automated)

### Setup

1. **Configure GitHub Secrets** (Repository → Settings → Secrets):
   - `DB_HOST` - Production database host
   - `DB_PORT` - Database port (5432)
   - `DB_NAME` - Database name
   - `DB_USER` - Database username
   - `DB_PASS` - Database password
   - `API_FOOTBALL_KEY` - API-Football key (get free at api-football.com)

2. **Workflow runs automatically**:
   - Every Monday at 3 AM UTC
   - Or trigger manually from Actions tab

### Manual Trigger

1. Go to **Actions** tab
2. Select **Update Predictions** workflow
3. Click **Run workflow**
4. Choose options:
   - **Mode**: complete, finish, predict, retrain, or best-bets
   - **Leagues**: all (or specific: E0,SP1,D1,I1)
   - **Date range**: Optional

## Operation Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **complete** | Full new matchday flow | Before new matches |
| **finish** | Load results + evaluate | After matches finish |
| **predict** | Generate predictions only | Update odds/lines |
| **retrain** | Retrain ML models | Improve accuracy |
| **best-bets** | Generate best bets | Get top picks |

## File Structure

```
55sportsBet/
├── data/
│   ├── raw/                    # Historical results
│   │   ├── E0.csv             # Premier League results
│   │   ├── SP1.csv            # La Liga results
│   │   ├── D1.csv             # Bundesliga results
│   │   └── I1.csv             # Serie A results
│   ├── fixtures_E0.csv        # Premier League fixtures
│   ├── fixtures_SP1.csv       # La Liga fixtures
│   ├── fixtures_D1.csv        # Bundesliga fixtures
│   └── fixtures_I1.csv        # Serie A fixtures
├── scripts/
│   ├── download-latest-data.py    # Download results
│   └── download-fixtures.py       # Download fixtures
├── src/scripts/
│   ├── update_predictions.py      # Interactive version
│   └── run_update_automated.py    # Automated version
├── update-local.bat           # Local update script
├── update-fixtures.bat        # Fixture download script
└── .env                       # Local configuration
```

## Supported Leagues

| Code | League | Country |
|------|--------|---------|
| E0 | Premier League | England |
| SP1 | La Liga | Spain |
| D1 | Bundesliga | Germany |
| I1 | Serie A | Italy |

## Common Tasks

### Update All Leagues Locally

```bash
update-local.bat
# Select "all" when prompted
```

### Update Single League

```bash
python src/scripts/run_update_automated.py --mode complete --leagues E0
```

### Download Latest Fixtures

```bash
update-fixtures.bat
```

### Check Workflow Status

1. Go to GitHub repository
2. Click **Actions** tab
3. View recent runs and logs

## Troubleshooting

### "No CSV data found"
- Run `python scripts/download-latest-data.py` first
- Check files exist in `data/raw/`

### "0 evaluations processed"
- Ensure CSV files contain data
- Check database connection
- Verify .env file is configured

### "API key invalid" (fixtures)
- Get free key at https://www.api-football.com/
- Add to .env: `API_FOOTBALL_KEY=your_key`
- Verify key is active in dashboard

### "Rate limit exceeded"
- Free tier: 100 requests/day
- Wait 24 hours or upgrade plan
- Don't run scripts too frequently

### GitHub Actions fails
- Check secrets are configured
- View workflow logs for details
- Verify database is accessible from GitHub

## API Keys

### API-Football (for fixtures)

1. Visit https://www.api-football.com/
2. Sign up for free account
3. Copy API key from dashboard
4. Add to:
   - Local: `.env` file → `API_FOOTBALL_KEY=your_key`
   - GitHub: Repository Secrets → `API_FOOTBALL_KEY`

**Free tier**: 100 requests/day (enough for all leagues)

## Documentation

- [Full Automation Guide](docs/GITHUB_ACTIONS_GUIDE.md)
- [Fixtures Setup](docs/FIXTURES_SETUP.md)
- [Data Workflow](docs/DATA_WORKFLOW.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Local Execution](docs/LOCAL_EXECUTION_GUIDE.md)

## Support

- Check documentation in `docs/` folder
- Review workflow logs in Actions tab
- Verify CSV files were downloaded correctly
- Test database connection manually

## Quick Reference Commands

```bash
# Local setup
setup.bat

# Update all leagues (local)
update-local.bat

# Download fixtures
update-fixtures.bat

# Download results
python scripts/download-latest-data.py --season 2526

# Manual prediction run
python src/scripts/run_update_automated.py --mode complete --leagues all

# Interactive mode
python src/scripts/update_predictions.py
```

## Next Steps

1. ✅ Configure .env file with credentials
2. ✅ Get API-Football key (free)
3. ✅ Run `setup.bat` to install dependencies
4. ✅ Run `update-fixtures.bat` to download fixtures
5. ✅ Run `update-local.bat` to update database
6. ✅ Configure GitHub Secrets for automation
7. ✅ Trigger workflow manually to test

---

**Questions?** Check the detailed documentation in the `docs/` folder.
