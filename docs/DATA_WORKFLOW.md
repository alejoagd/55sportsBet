# Data Workflow Guide

This guide explains how data flows through the system in different environments.

## Data Sources

The system uses TWO data sources:

### 1. Historical Results: football-data.co.uk

For completed matches with results and odds.

| Code | League | URL Pattern |
|------|--------|-------------|
| `E0` | Premier League | `https://www.football-data.co.uk/mmz4281/{season}/E0.csv` |
| `SP1` | La Liga | `https://www.football-data.co.uk/mmz4281/{season}/SP1.csv` |
| `D1` | Bundesliga | `https://www.football-data.co.uk/mmz4281/{season}/D1.csv` |
| `I1` | Serie A | `https://www.football-data.co.uk/mmz4281/{season}/I1.csv` |

Season format: `2425` = 2024/2025

### 2. Upcoming Fixtures: API-Football

For future matches to predict.

| Code | League | API League ID |
|------|--------|---------------|
| `E0` | Premier League | 39 |
| `SP1` | La Liga | 140 |
| `D1` | Bundesliga | 78 |
| `I1` | Serie A | 135 |

**Note**: Requires free API key from [api-football.com](https://www.api-football.com/)
**Free tier**: 100 requests/day (sufficient for all 4 leagues)

## Local Development Workflow

### Manual Data Update

```bash
# 1. Download CSV manually from football-data.co.uk
# 2. Place in data/raw/ directory
# 3. Run update script

python src/scripts/update_predictions.py
```

### Automated Data Download

#### Historical Results
```bash
# Download latest data for all leagues
python scripts/download-latest-data.py

# Download for specific season
python scripts/download-latest-data.py --season 2526

# Download specific leagues
python scripts/download-latest-data.py --leagues "E0,SP1"

# Custom output directory
python scripts/download-latest-data.py --output data/raw
```

#### Upcoming Fixtures
```bash
# Download fixtures for all leagues
python scripts/download-fixtures.py --season 2025

# Download specific leagues
python scripts/download-fixtures.py --leagues "E0,SP1" --season 2025

# Requires API key (add to .env file):
# API_FOOTBALL_KEY=your_key_here
```

#### Quick Update (Windows)
```bash
# Download fixtures only
update-fixtures.bat

# Download results only
# (not needed separately - included in update-local.bat)

# Full update (results + predictions)
update-local.bat
```

## GitHub Actions Workflow

The GitHub Actions pipeline **automatically downloads** fresh data before running:

```yaml
- name: Download latest CSV data
  run: |
    python scripts/download-latest-data.py --season 2425 --leagues all
```

### Data Flow in GitHub Actions

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions Execution                               │
└─────────────────────────────────────────────────────────┘

1. Checkout code
2. Install Python & dependencies

3. ✅ Download latest CSV data (RESULTS) ← AUTOMATIC
   │
   ├─ Downloads E0.csv (Premier League)
   ├─ Downloads SP1.csv (La Liga)
   ├─ Downloads D1.csv (Bundesliga)
   └─ Downloads I1.csv (Serie A)

4. ✅ Download upcoming fixtures ← AUTOMATIC
   │
   ├─ Downloads fixtures_E0.csv (Premier League)
   ├─ Downloads fixtures_SP1.csv (La Liga)
   ├─ Downloads fixtures_D1.csv (Bundesliga)
   └─ Downloads fixtures_I1.csv (Serie A)

5. Create .env.production

6. Run prediction updates
   │
   ├─ Load results CSV → Database
   ├─ Load fixtures CSV → Database
   ├─ Generate predictions
   ├─ Create betting lines
   └─ Generate best bets
```

## Data Storage Options

### Option 1: Git-Tracked Data (Current Setup)

**Pros:**
- Simple
- No external dependencies during workflow
- Faster workflow execution

**Cons:**
- Repository size increases
- Need to manually update CSVs
- May have stale data

**Setup:**
```bash
# Add data files to git
git add data/raw/*.csv data/fixtures_*.csv
git commit -m "Add data files"
git push
```

### Option 2: Auto-Download (Recommended - Implemented)

**Pros:**
- Always fresh data
- No manual updates needed
- Smaller repository

**Cons:**
- Depends on external website availability
- Slightly longer workflow time

**Setup:**
Already configured in workflow! No action needed.

### Option 3: Cloud Storage (Advanced)

Store CSV files in cloud storage (S3, Google Cloud Storage, etc.)

**Pros:**
- Centralized data management
- Can handle large datasets
- Version control

**Cons:**
- Additional cost
- More complex setup
- Requires credentials

## Updating Season

When a new season starts, update the season code:

### In GitHub Actions

Edit [.github/workflows/update-predictions.yml](.github/workflows/update-predictions.yml):

```yaml
- name: Download latest CSV data
  run: |
    python scripts/download-latest-data.py --season 2526 --leagues all  # ← Update here
```

### Locally

```bash
# Download new season data
python scripts/download-latest-data.py --season 2526
```

## Data Validation

The download script validates data automatically:

```python
# Checks performed:
✅ HTTP response status
✅ File size > 0
✅ Valid CSV format
✅ Row count > 0
```

If download fails, the workflow will exit with an error.

## Troubleshooting

### "No data found" in workflow

**Cause**: CSV files not available or not downloaded

**Solutions**:
1. Check if download step succeeded in workflow logs
2. Verify season code is correct (e.g., `2425` not `2024`)
3. Check football-data.co.uk website is accessible
4. Try downloading manually to verify URL

### "File not found" error

**Cause**: CSV files missing from expected location

**Solutions**:
```bash
# Verify files exist
ls -la data/raw/

# Re-download
python scripts/download-latest-data.py

# Check workflow downloaded files
# (in GitHub Actions logs, look for "Download latest CSV data" step)
```

### Stale Data

**Cause**: Using old CSV files

**Solutions**:
```bash
# Force fresh download
rm data/raw/*.csv
python scripts/download-latest-data.py
```

## Best Practices

1. **Local Development**: Use auto-download script for fresh data
   ```bash
   python scripts/download-latest-data.py
   ```

2. **GitHub Actions**: Let workflow handle downloads automatically

3. **Season Changes**: Update season code in both:
   - Workflow file
   - Local commands

4. **Data Verification**: Check downloaded row counts match expectations

5. **Backup**: Keep a backup of historical data if needed

## Workflow Summary

### Local

```bash
# One-time setup
python scripts/download-latest-data.py

# Regular updates
python src/scripts/update_predictions.py
```

### GitHub Actions

```bash
# Runs automatically on schedule
# OR trigger manually

# Workflow handles:
# 1. Download data
# 2. Update database
# 3. Generate predictions
```

---

**Questions?**
- Check workflow logs in Actions tab
- Verify CSV files in `data/raw/`
- Run download script manually to test
