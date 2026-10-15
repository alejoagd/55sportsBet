# GitHub Actions Pipeline - Quick Start

I've created a complete GitHub Actions pipeline to automate your prediction updates. Here's what was added:

## 📁 Files Created

### 1. GitHub Actions Workflow
- **Location**: [.github/workflows/update-predictions.yml](.github/workflows/update-predictions.yml)
- **Purpose**: Main workflow that runs in GitHub Actions
- **Database**: ⚠️ **PRODUCTION ONLY** (cannot access localhost)
- **Features**:
  - ✅ Manual trigger with custom parameters
  - ✅ Scheduled execution (Mondays at 3 AM UTC)
  - ✅ 5 operation modes
  - ✅ Multi-league support

### 2. Automated Script
- **Location**: [src/scripts/run_update_automated.py](src/scripts/run_update_automated.py)
- **Purpose**: Non-interactive version of `update_predictions.py` for CI/CD
- **Database**: ✅ **LOCAL or PRODUCTION** (configurable with `--env-file`)
- **Features**:
  - ✅ Command-line arguments
  - ✅ No user input required
  - ✅ Full error handling
  - ✅ Automated logging

### 3. Documentation
- **Location**: [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md)
- **Purpose**: Complete guide for using the pipeline
- **Includes**:
  - Setup instructions
  - Usage examples
  - Troubleshooting
  - Best practices

### 4. Setup Script
- **Location**: [scripts/setup-github-secrets.sh](scripts/setup-github-secrets.sh)
- **Purpose**: Easy configuration of GitHub secrets
- **Features**:
  - ✅ Interactive setup
  - ✅ Reads from .env.production
  - ✅ Uses GitHub CLI

### 5. Local Execution Scripts (Windows)
- **Location**: [update-local.bat](update-local.bat) and [update-prod.bat](update-prod.bat)
- **Purpose**: Easy local execution for updating databases
- **Features**:
  - ✅ Simple command-line interface
  - ✅ `update-local.bat` - Updates LOCAL database
  - ✅ `update-prod.bat` - Updates PRODUCTION database (from your PC)
  - ✅ Automatic virtual environment activation

### 6. Local Execution Guide
- **Location**: [docs/LOCAL_EXECUTION_GUIDE.md](docs/LOCAL_EXECUTION_GUIDE.md)
- **Purpose**: Complete guide for running locally
- **Includes**:
  - Local vs GitHub Actions comparison
  - Windows/Linux/Mac instructions
  - Scheduling with Task Scheduler/Cron

## ⚠️ Important: Local vs Production Database

### GitHub Actions (Cloud)
- ✅ Runs on GitHub's servers
- ✅ Good for **PRODUCTION** database (remote servers like Render)
- ❌ **CANNOT access localhost** database

### Local Execution (Your Computer)
- ✅ Runs on your machine
- ✅ Can access **LOCALHOST** database
- ✅ Can also access **PRODUCTION** database
- ✅ Full control

**Summary**:
- To update **LOCAL** database → Run scripts locally on your PC
- To update **PRODUCTION** database → Use GitHub Actions OR run locally

## 🚀 Quick Setup (3 Steps)

### Step 1: Configure GitHub Secrets

You need to add these secrets to your GitHub repository:

| Secret | Description |
|--------|-------------|
| `DB_HOST` | PostgreSQL host (e.g., `dpg-xxxxx.render.com`) |
| `DB_PORT` | PostgreSQL port (e.g., `5432`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_SCHEMA` | Database schema (e.g., `public`) |
| `API_URL` | Your API URL (e.g., `https://your-api.onrender.com`) |

#### Option A: Using the Setup Script (Recommended)

```bash
# Make script executable
chmod +x scripts/setup-github-secrets.sh

# Run setup
./scripts/setup-github-secrets.sh
```

#### Option B: Manual Setup via GitHub Web

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret one by one

#### Option C: Using GitHub CLI

```bash
gh secret set DB_HOST --body "your-db-host"
gh secret set DB_PORT --body "5432"
gh secret set DB_NAME --body "your-db-name"
gh secret set DB_USER --body "your-db-user"
gh secret set DB_PASSWORD --body "your-password"
gh secret set DB_SCHEMA --body "public"
gh secret set API_URL --body "https://your-api.onrender.com"
```

### Step 2: Commit and Push

```bash
git add .github/workflows/update-predictions.yml
git add src/scripts/run_update_automated.py
git add docs/GITHUB_ACTIONS_GUIDE.md
git add scripts/setup-github-secrets.sh
git add GITHUB_ACTIONS_SETUP.md

git commit -m "Add GitHub Actions pipeline for automated predictions"
git push origin main
```

### Step 3: Test the Workflow

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Select **Update Predictions** workflow
4. Click **Run workflow**
5. Configure parameters:
   - **Operation mode**: `predict`
   - **Date from**: `2024-03-10` (adjust to your needs)
   - **Date to**: `2024-03-16` (adjust to your needs)
   - **Leagues**: `all`
6. Click **Run workflow**

## 📋 Operation Modes

### 1. `complete` - Pre-Match Flow
Executes: RETRAIN → PREDICT → BETTING LINES → BEST BETS

**Use before matches start**

```bash
# Via GitHub CLI
gh workflow run update-predictions.yml \
  -f operation_mode=complete \
  -f date_from=2024-03-11 \
  -f date_to=2024-03-17 \
  -f leagues=all
```

### 2. `finish` - Post-Match Flow
Executes: EVALUATE → VALIDATE BETTING → VALIDATE BEST BETS

**Use after matches end**

```bash
gh workflow run update-predictions.yml \
  -f operation_mode=finish \
  -f date_from=2024-03-04 \
  -f date_to=2024-03-10 \
  -f leagues=all
```

### 3. `predict` - Predictions Only
Generates Poisson and Weinston predictions

```bash
gh workflow run update-predictions.yml \
  -f operation_mode=predict \
  -f date_from=2024-03-11 \
  -f date_to=2024-03-17 \
  -f leagues="E0,SP1"
```

### 4. `retrain` - Model Training Only
Re-trains the Weinston model

```bash
gh workflow run update-predictions.yml \
  -f operation_mode=retrain \
  -f leagues=all
```

### 5. `best-bets` - Best Bets Only
Generates best betting opportunities

```bash
gh workflow run update-predictions.yml \
  -f operation_mode=best-bets \
  -f date_from=2024-03-11 \
  -f date_to=2024-03-17 \
  -f leagues=all
```

## 🕐 Scheduled Execution

By default, the workflow runs **every Monday at 3 AM UTC**.

To change this, edit [.github/workflows/update-predictions.yml](.github/workflows/update-predictions.yml):

```yaml
schedule:
  - cron: '0 3 * * 1'  # Current: Mondays at 3 AM
  # Examples:
  # - cron: '0 0 * * *'     # Daily at midnight
  # - cron: '0 2 * * 1,4'   # Monday & Thursday at 2 AM
  # - cron: '0 */6 * * *'   # Every 6 hours
```

## 🏆 League Codes

| Code | League |
|------|--------|
| `E0` | English Premier League |
| `SP1` | Spanish La Liga |
| `D1` | German Bundesliga |
| `I1` | Italian Serie A |
| `all` | All available leagues |

Examples:
- Single league: `E0`
- Multiple leagues: `E0,SP1,D1`
- All leagues: `all`

## 💻 Local Execution (for LOCAL database)

### Using Batch Scripts (Windows - Easiest)

I've created convenient batch scripts for you:

#### Update LOCAL Database

```cmd
REM Complete flow (pre-match)
update-local.bat complete 2024-03-11 2024-03-17 all

REM Finish flow (post-match)
update-local.bat finish 2024-03-04 2024-03-10 all

REM Predict only for specific leagues
update-local.bat predict 2024-03-11 2024-03-17 "E0,SP1"

REM Retrain model
update-local.bat retrain all

REM Best bets only
update-local.bat best-bets 2024-03-11 2024-03-17 all
```

#### Update PRODUCTION Database (from your PC)

```cmd
REM Complete flow (pre-match)
update-prod.bat complete 2024-03-11 2024-03-17 all

REM Finish flow (post-match)
update-prod.bat finish 2024-03-04 2024-03-10 all

REM Predict only
update-prod.bat predict 2024-03-11 2024-03-17 all
```

### Using Python Directly

```bash
# LOCAL database
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env

# PRODUCTION database (from your PC)
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env.production
```

### Complete Local Execution Guide

For detailed instructions including Linux/Mac, scheduling, and troubleshooting:

📖 **Read**: [docs/LOCAL_EXECUTION_GUIDE.md](docs/LOCAL_EXECUTION_GUIDE.md)

## 🧪 Local Testing

Test the automated script locally before using in GitHub Actions:

```bash
# Test complete flow
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env.production

# Test with specific leagues
python src/scripts/run_update_automated.py \
  --mode predict \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues "E0,SP1" \
  --env-file .env

# Test retrain
python src/scripts/run_update_automated.py \
  --mode retrain \
  --leagues all \
  --env-file .env
```

## 📊 Monitoring

### View Workflow Status
1. Go to **Actions** tab on GitHub
2. Click on a workflow run
3. View logs and status

### Download Logs
Each run saves logs as artifacts (retained for 30 days):
1. Go to completed workflow run
2. Scroll to **Artifacts**
3. Download `prediction-update-logs-{run_number}`

### Notifications
- ✅ **Success**: Workflow completes normally
- ❌ **Failure**: Error message shown in logs
- ⚠️ **Warnings**: Some leagues processed with issues

## 🛠️ Troubleshooting

### Common Issues

**Database Connection Failed**
- ✅ Check secrets are configured correctly
- ✅ Verify database is accessible
- ✅ Ensure DB_PASSWORD is correct

**API Connection Failed**
- ✅ Check API_URL is correct
- ✅ Verify API server is running
- ✅ Ensure API endpoints are accessible

**League Not Found**
- ✅ Use correct codes: E0, SP1, D1, I1
- ✅ Or use "all" for all leagues

**Date Format Error**
- ✅ Use YYYY-MM-DD format
- ✅ Example: 2024-03-11

## 📖 Full Documentation

For complete details, see [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md)

## 🎯 Typical Weekly Workflow

### Monday Morning (Automated)
```
Schedule triggers at 3 AM UTC
→ Runs "complete" mode
→ Prepares predictions for upcoming matches
```

### Manual Execution After Matches
```bash
# Update results and validate
gh workflow run update-predictions.yml \
  -f operation_mode=finish \
  -f date_from=2024-03-04 \
  -f date_to=2024-03-10 \
  -f leagues=all
```

## ✨ Next Steps

1. ✅ Configure GitHub secrets
2. ✅ Push the files to GitHub
3. ✅ Test with a manual workflow run
4. ✅ Monitor the scheduled runs
5. ✅ Adjust schedule as needed

---

**Need Help?**
- Read [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md)
- Check workflow logs in Actions tab
- Review error messages and troubleshooting section
