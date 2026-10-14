# Automation Summary - Complete Guide

## 📋 What Was Created

I've created a complete automation system for your prediction updates with support for BOTH local and production databases.

### Files Created

1. **GitHub Actions Workflow** - [.github/workflows/update-predictions.yml](.github/workflows/update-predictions.yml)
   - For PRODUCTION database only
   - Runs on GitHub's servers

2. **Automated Python Script** - [src/scripts/run_update_automated.py](src/scripts/run_update_automated.py)
   - Works with BOTH local and production
   - Command-line interface

3. **Windows Batch Scripts** - [update-local.bat](update-local.bat) & [update-prod.bat](update-prod.bat)
   - Easy execution on Windows
   - Automatic environment activation

4. **Documentation**:
   - [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) - GitHub Actions guide
   - [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md) - Complete GitHub Actions reference
   - [docs/LOCAL_EXECUTION_GUIDE.md](docs/LOCAL_EXECUTION_GUIDE.md) - Local execution guide

5. **Setup Script** - [scripts/setup-github-secrets.sh](scripts/setup-github-secrets.sh)
   - Configure GitHub secrets easily

## 🎯 Answer to Your Question

### "Can I update my local database?"

**YES!** You have THREE options:

#### Option 1: Update LOCAL Database (Using Batch Script - EASIEST)

```cmd
update-local.bat complete 2024-03-11 2024-03-17 all
```

This will:
- ✅ Use your `.env` file
- ✅ Connect to `localhost` database
- ✅ Run complete prediction flow

#### Option 2: Update LOCAL Database (Using Python)

```bash
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-03-11 \
  --date-to 2024-03-17 \
  --leagues all \
  --env-file .env
```

#### Option 3: Update PRODUCTION Database (From Your PC)

```cmd
update-prod.bat complete 2024-03-11 2024-03-17 all
```

Or use GitHub Actions (automatic).

## 🔄 How It Works

### Your Original Script (`update_predictions.py`)
- ✅ Interactive (asks questions)
- ✅ Lets you choose database (localhost or production)
- ✅ Manual execution

### New Automated Script (`run_update_automated.py`)
- ✅ Non-interactive (no questions)
- ✅ Choose database via `--env-file` parameter
- ✅ Can run in GitHub Actions or locally

## 📊 Comparison Table

| Method | Database | Where it Runs | When to Use |
|--------|----------|---------------|-------------|
| **GitHub Actions** | Production only | GitHub servers | Automatic production updates |
| **Batch Scripts** | Local or Production | Your computer | Quick local/prod updates |
| **Python Script** | Local or Production | Your computer | Full control, scripting |
| **Original Interactive** | Local or Production | Your computer | Manual with prompts |

## 🚀 Quick Start Guide

### For LOCAL Database Updates

**1. Make sure you have `.env` file**:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_local_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_SCHEMA=public
API_URL=http://localhost:8000
```

**2. Run the batch script**:

```cmd
REM Navigate to project directory
cd C:\Users\Hp\Documents\55sportsBet\55sportsBet

REM Run complete flow
update-local.bat complete 2024-03-11 2024-03-17 all
```

### For PRODUCTION Database Updates

**Option A: Using GitHub Actions (Recommended for Production)**

1. Configure GitHub secrets (one-time setup)
2. Go to Actions tab → Run workflow
3. Select parameters and run

**Option B: From Your Local Computer**

**1. Make sure you have `.env.production` file**:

```env
DB_HOST=dpg-xxxxx.render.com
DB_PORT=5432
DB_NAME=your_prod_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_SCHEMA=public
API_URL=https://your-api.onrender.com
```

**2. Run the batch script**:

```cmd
update-prod.bat complete 2024-03-11 2024-03-17 all
```

## 📖 Complete Examples

### Typical Weekly Workflow

#### Monday Morning - Pre-Match Predictions

**Test on LOCAL first**:
```cmd
REM Test with one league
update-local.bat complete 2024-03-11 2024-03-17 "E0"

REM If successful, run all leagues
update-local.bat complete 2024-03-11 2024-03-17 all
```

**Then update PRODUCTION**:

Option 1 - Via GitHub Actions (automatic at 3 AM) ✅

Option 2 - Manually from your PC:
```cmd
update-prod.bat complete 2024-03-11 2024-03-17 all
```

#### Sunday Evening - Post-Match Validation

**LOCAL**:
```cmd
update-local.bat finish 2024-03-04 2024-03-10 all
```

**PRODUCTION**:
```cmd
update-prod.bat finish 2024-03-04 2024-03-10 all
```

Or trigger GitHub Actions manually.

### All Available Commands

#### LOCAL Database

```cmd
REM Complete flow (RETRAIN → PREDICT → BETTING LINES → BEST BETS)
update-local.bat complete 2024-03-11 2024-03-17 all

REM Finish flow (EVALUATE → VALIDATE)
update-local.bat finish 2024-03-04 2024-03-10 all

REM Just predictions
update-local.bat predict 2024-03-11 2024-03-17 all

REM Just retrain model
update-local.bat retrain all

REM Just best bets
update-local.bat best-bets 2024-03-11 2024-03-17 all

REM Specific leagues only
update-local.bat predict 2024-03-11 2024-03-17 "E0,SP1,D1"
```

#### PRODUCTION Database

```cmd
REM Same commands, just use update-prod.bat instead
update-prod.bat complete 2024-03-11 2024-03-17 all
update-prod.bat finish 2024-03-04 2024-03-10 all
update-prod.bat predict 2024-03-11 2024-03-17 all
update-prod.bat retrain all
update-prod.bat best-bets 2024-03-11 2024-03-17 all
```

## 🎓 Understanding the Architecture

### Environment Files

```
.env                  → LOCAL database credentials
.env.production       → PRODUCTION database credentials
```

The `--env-file` parameter tells the script which database to use:
- `--env-file .env` → localhost
- `--env-file .env.production` → production

### Batch Scripts

The batch scripts are just shortcuts:

```batch
REM update-local.bat is essentially:
python src\scripts\run_update_automated.py --env-file .env <your-args>

REM update-prod.bat is essentially:
python src\scripts\run_update_automated.py --env-file .env.production <your-args>
```

### GitHub Actions Workflow

The workflow file is configured to ONLY use `.env.production` because:
- GitHub Actions runs on GitHub's servers (in the cloud)
- It cannot access your localhost database
- It creates `.env.production` from GitHub Secrets

## 🛠️ Setup Steps

### 1. For Local Execution (LOCAL database)

✅ Already works! Just run:
```cmd
update-local.bat complete 2024-03-11 2024-03-17 all
```

### 2. For GitHub Actions (PRODUCTION database)

**Step 1**: Configure GitHub secrets

```bash
gh secret set DB_HOST --body "your-prod-host"
gh secret set DB_PORT --body "5432"
gh secret set DB_NAME --body "your-prod-db"
gh secret set DB_USER --body "your-prod-user"
gh secret set DB_PASSWORD --body "your-prod-password"
gh secret set DB_SCHEMA --body "public"
gh secret set API_URL --body "https://your-api.onrender.com"
```

Or use the setup script:
```bash
chmod +x scripts/setup-github-secrets.sh
./scripts/setup-github-secrets.sh
```

**Step 2**: Commit and push

```bash
git add .
git commit -m "Add automation pipeline"
git push origin main
```

**Step 3**: Test it

Go to Actions tab → Update Predictions → Run workflow

### 3. For Local Execution (PRODUCTION database from your PC)

**Step 1**: Create `.env.production` file with production credentials

**Step 2**: Run:
```cmd
update-prod.bat complete 2024-03-11 2024-03-17 all
```

## 📚 Documentation Links

- **Quick Start**: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
- **GitHub Actions Guide**: [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md)
- **Local Execution Guide**: [docs/LOCAL_EXECUTION_GUIDE.md](docs/LOCAL_EXECUTION_GUIDE.md)

## 🔧 Troubleshooting

### "Can't connect to localhost"

**For LOCAL database**:
1. Make sure PostgreSQL is running on your computer
2. Check `.env` has correct credentials
3. Test connection: `psql -h localhost -U postgres -d your_db`

**For PRODUCTION database**:
1. Check `.env.production` has correct credentials
2. Make sure you have internet connection
3. Verify production database is accessible

### "Script not found"

Make sure you're in the project root directory:
```cmd
cd C:\Users\Hp\Documents\55sportsBet\55sportsBet
```

### "Virtual environment not found"

The batch scripts will warn you but still work. To create venv:
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 🎯 Recommended Workflow

### Development Phase
1. ✅ Test on LOCAL database using `update-local.bat`
2. ✅ Verify results
3. ✅ When satisfied, update production

### Production Updates

**Automatic** (Recommended):
- Let GitHub Actions run on schedule (Mondays 3 AM)

**Manual**:
```cmd
REM From your PC
update-prod.bat complete 2024-03-11 2024-03-17 all

REM Or via GitHub Actions
gh workflow run update-predictions.yml -f operation_mode=complete -f date_from=2024-03-11 -f date_to=2024-03-17 -f leagues=all
```

## ✨ Summary

**You now have 3 ways to update databases**:

1. **Interactive** (original): `python src/scripts/update_predictions.py`
   - Asks questions, choose database interactively

2. **Local Automated** (new): `update-local.bat` or `update-prod.bat`
   - Quick, easy, works from your PC
   - Can update LOCAL or PRODUCTION

3. **GitHub Actions** (new): Fully automated in the cloud
   - PRODUCTION only
   - Scheduled or manual trigger

**Choose based on your needs**:
- Development/Testing → Use `update-local.bat`
- Production (manual) → Use `update-prod.bat` or GitHub Actions UI
- Production (automatic) → GitHub Actions scheduled runs

---

**Need Help?**
- Quick questions → Read [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
- Local execution → Read [docs/LOCAL_EXECUTION_GUIDE.md](docs/LOCAL_EXECUTION_GUIDE.md)
- GitHub Actions → Read [docs/GITHUB_ACTIONS_GUIDE.md](docs/GITHUB_ACTIONS_GUIDE.md)
