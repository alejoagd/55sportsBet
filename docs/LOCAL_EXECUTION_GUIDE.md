# Local Execution Guide - Automated Updates

This guide explains how to run the automated prediction updates on your **local machine** to update your **local database**.

## Important: GitHub Actions vs Local Execution

### GitHub Actions (Cloud)
- ✅ Runs on GitHub's servers
- ✅ Good for production database (remote)
- ❌ **Cannot access localhost database**

### Local Execution (Your Computer)
- ✅ Runs on your machine
- ✅ Can access localhost database
- ✅ Can access production database (remote)
- ✅ Full control over execution

## Local Execution - Quick Start

### Prerequisites

1. Python 3.11+ installed
2. Virtual environment activated
3. All dependencies installed (`pip install -r requirements.txt`)
4. `.env` file configured for localhost

### Your `.env` File (Localhost)

Create/verify your `.env` file in the project root:

```env
# Local Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_local_db_name
DB_USER=postgres
DB_PASSWORD=your_local_password
DB_SCHEMA=public

# Local API (if running locally)
API_URL=http://localhost:8000
```

### Your `.env.production` File (Production)

For production database access from your local machine:

```env
# Production Database Configuration
DB_HOST=dpg-xxxxx.render.com
DB_PORT=5432
DB_NAME=your_prod_db_name
DB_USER=your_prod_user
DB_PASSWORD=your_prod_password
DB_SCHEMA=public

# Production API
API_URL=https://your-api.onrender.com
```

## Running Locally

### Basic Usage

```bash
# Activate your virtual environment first
source .venv/bin/activate  # On Linux/Mac
.venv\Scripts\activate     # On Windows

# Run automated script
python src/scripts/run_update_automated.py \
  --mode <MODE> \
  --date-from <DATE> \
  --date-to <DATE> \
  --leagues <LEAGUES> \
  --env-file <ENV_FILE>
```

### Examples - LOCAL Database

#### 1. Complete Flow (Pre-Match) - Local Database

```bash
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env
```

**What it does**:
1. ✅ Connects to **localhost** database
2. ✅ Retrains Weinston model
3. ✅ Generates predictions
4. ✅ Creates betting lines
5. ✅ Generates best bets

#### 2. Finish Flow (Post-Match) - Local Database

```bash
python src/scripts/run_update_automated.py \
  --mode finish \
  --date-from 2024-03-04 \
  --date-to 2024-03-10 \
  --leagues all \
  --env-file .env
```

**What it does**:
1. ✅ Connects to **localhost** database
2. ✅ Evaluates predictions vs results
3. ✅ Validates betting lines
4. ✅ Validates best bets

#### 3. Predict Only - Local Database

```bash
python src/scripts/run_update_automated.py \
  --mode predict \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues "E0,SP1" \
  --env-file .env
```

#### 4. Retrain Model - Local Database

```bash
python src/scripts/run_update_automated.py \
  --mode retrain \
  --leagues all \
  --env-file .env
```

#### 5. Best Bets Only - Local Database

```bash
python src/scripts/run_update_automated.py \
  --mode best-bets \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env
```

### Examples - PRODUCTION Database (from your local machine)

You can also update your production database from your local machine:

```bash
# Complete flow - Production
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env.production

# Finish flow - Production
python src/scripts/run_update_automated.py \
  --mode finish \
  --date-from 2024-03-04 \
  --date-to 2024-03-10 \
  --leagues all \
  --env-file .env.production
```

## Creating Shortcuts/Aliases

### For Linux/Mac - Bash Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Alias for local database updates
alias update-local="python src/scripts/run_update_automated.py --env-file .env"
alias update-prod="python src/scripts/run_update_automated.py --env-file .env.production"

# Usage examples:
# update-local --mode complete --date-from 2024-03-11 --date-to 2024-03-17 --leagues all
# update-prod --mode finish --date-from 2024-03-04 --date-to 2024-03-10 --leagues all
```

### For Windows - Batch Scripts

Create `update-local.bat` in your project root:

```batch
@echo off
python src\scripts\run_update_automated.py --env-file .env %*
```

Create `update-prod.bat`:

```batch
@echo off
python src\scripts\run_update_automated.py --env-file .env.production %*
```

**Usage**:
```cmd
REM Local database
update-local --mode complete --date-from 2024-03-11 --date-to 2024-03-17 --leagues all

REM Production database
update-prod --mode finish --date-from 2024-03-04 --date-to 2024-03-10 --leagues all
```

### For Windows - PowerShell Functions

Add to your PowerShell profile (`$PROFILE`):

```powershell
function Update-Local {
    python src/scripts/run_update_automated.py --env-file .env $args
}

function Update-Prod {
    python src/scripts/run_update_automated.py --env-file .env.production $args
}

# Usage:
# Update-Local --mode complete --date-from 2024-03-11 --date-to 2024-03-17 --leagues all
# Update-Prod --mode finish --date-from 2024-03-04 --date-to 2024-03-10 --leagues all
```

## Scheduling Local Execution

### Using Windows Task Scheduler

1. Open **Task Scheduler**
2. Click **Create Task**
3. **General** tab:
   - Name: "Update Sports Predictions"
   - Run whether user is logged on or not
4. **Triggers** tab:
   - New trigger
   - Weekly, every Monday at 3:00 AM
5. **Actions** tab:
   - Action: Start a program
   - Program: `C:\Python311\python.exe`
   - Arguments: `src\scripts\run_update_automated.py --mode complete --date-from 2024-03-11 --date-to 2024-03-17 --leagues all --env-file .env`
   - Start in: `C:\Users\Hp\Documents\55sportsBet\55sportsBet`

### Using Linux/Mac Cron

Edit crontab:
```bash
crontab -e
```

Add entry:
```cron
# Run every Monday at 3 AM
0 3 * * 1 cd /path/to/55sportsBet && /path/to/.venv/bin/python src/scripts/run_update_automated.py --mode complete --date-from $(date -d 'next monday' +\%Y-\%m-\%d) --date-to $(date -d 'next monday +6 days' +\%Y-\%m-\%d) --leagues all --env-file .env
```

## Comparison: Local vs GitHub Actions

| Feature | Local Execution | GitHub Actions |
|---------|----------------|----------------|
| Database Access | ✅ Localhost + Remote | ❌ Remote only |
| Requires Computer On | ✅ Yes | ❌ No |
| Free | ✅ Yes | ✅ Yes (with limits) |
| Setup Complexity | ⭐ Easy | ⭐⭐ Medium |
| Automation | ⭐⭐ (Task Scheduler/Cron) | ⭐⭐⭐ (Built-in) |
| Logging | 📝 Local files | 📝 GitHub artifacts |
| Best For | Development/Testing | Production |

## Recommended Workflow

### For Development (Local Database)

```bash
# 1. Update fixtures locally
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env

# 2. Test and verify locally

# 3. When ready, push to production via GitHub Actions
```

### For Production

Use **GitHub Actions** (automatic) or run from your local machine:

```bash
# Option 1: Let GitHub Actions handle it (recommended)
# - Runs automatically on schedule
# - Or trigger manually from GitHub web UI

# Option 2: Run from local machine to production database
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env.production
```

## Typical Weekly Routine

### Monday (Pre-Match)

**Local Testing**:
```bash
# Test on localhost first
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues "E0" \
  --env-file .env

# If successful, run for all leagues
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env
```

**Production** (automatic via GitHub Actions or manual):
```bash
# Manual if needed
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env.production
```

### Sunday/Monday (Post-Match)

**Local**:
```bash
python src/scripts/run_update_automated.py \
  --mode finish \
  --date-from 2024-03-04 \
  --date-to 2024-03-10 \
  --leagues all \
  --env-file .env
```

**Production**:
```bash
# Via GitHub Actions or:
python src/scripts/run_update_automated.py \
  --mode finish \
  --date-from 2024-03-04 \
  --date-to 2024-03-10 \
  --leagues all \
  --env-file .env.production
```

## Troubleshooting Local Execution

### Database Connection Failed

**Check**:
```bash
# Verify PostgreSQL is running
# Windows:
services.msc  # Look for "PostgreSQL"

# Linux/Mac:
sudo systemctl status postgresql
# or
pg_ctl status
```

**Test connection**:
```bash
psql -h localhost -U postgres -d your_db_name
```

### API Connection Failed

**Check if API is running**:
```bash
# Start your API locally first
uvicorn src.main:app --reload

# Then run the update script
```

### Environment File Not Found

**Error**: `Archivo no encontrado: .env`

**Solution**:
```bash
# Make sure you're in the project root
cd /path/to/55sportsBet

# Verify .env exists
ls -la .env

# Create if missing
cp .env.example .env  # If you have an example
# or create manually
```

## Advanced: Self-Hosted GitHub Actions Runner

If you want GitHub Actions to access your localhost, you can set up a self-hosted runner:

1. Go to **Settings** → **Actions** → **Runners**
2. Click **New self-hosted runner**
3. Follow instructions for your OS
4. The runner will execute workflows on your local machine
5. Can access localhost database

**Note**: This is advanced and usually not needed. Local execution is simpler.

## Quick Reference

### Update Local Database
```bash
# Pre-match (complete)
python src/scripts/run_update_automated.py --mode complete --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env

# Post-match (finish)
python src/scripts/run_update_automated.py --mode finish --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env
```

### Update Production Database (from local machine)
```bash
# Pre-match (complete)
python src/scripts/run_update_automated.py --mode complete --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env.production

# Post-match (finish)
python src/scripts/run_update_automated.py --mode finish --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env.production
```

### Update Production via GitHub Actions
```bash
# Trigger from command line
gh workflow run update-predictions.yml -f operation_mode=complete -f date_from=YYYY-MM-DD -f date_to=YYYY-MM-DD -f leagues=all
```

---

**Summary**:
- Use **local execution** with `.env` for localhost database
- Use **local execution** with `.env.production` or **GitHub Actions** for production database
- GitHub Actions **cannot** access localhost (runs on GitHub's servers)
