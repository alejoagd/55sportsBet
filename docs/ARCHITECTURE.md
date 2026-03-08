# Architecture Diagram - Automation System

## Database Update Options

```
┌─────────────────────────────────────────────────────────────────────┐
│                    YOUR AUTOMATION OPTIONS                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  OPTION 1: Update LOCAL Database (from your PC)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Your Computer                    Localhost Database                │
│  ┌──────────────┐                ┌──────────────┐                  │
│  │              │   connects to  │              │                  │
│  │ Batch Script ├───────────────→│  PostgreSQL  │                  │
│  │ (update-     │   uses .env    │  localhost   │                  │
│  │  local.bat)  │                │  port 5432   │                  │
│  │              │                │              │                  │
│  └──────────────┘                └──────────────┘                  │
│        │                                                            │
│        │ runs                                                       │
│        ↓                                                            │
│  ┌──────────────────────────────────┐                              │
│  │ run_update_automated.py          │                              │
│  │ --env-file .env                  │                              │
│  └──────────────────────────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  OPTION 2: Update PRODUCTION Database (from your PC)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Your Computer                    Production Database               │
│  ┌──────────────┐                ┌──────────────────┐              │
│  │              │   connects to  │                  │              │
│  │ Batch Script ├───────────────→│  PostgreSQL      │              │
│  │ (update-     │  uses .env.    │  Render/AWS      │              │
│  │  prod.bat)   │  production    │  (remote server) │              │
│  │              │                │                  │              │
│  └──────────────┘                └──────────────────┘              │
│        │                                                            │
│        │ runs                                                       │
│        ↓                                                            │
│  ┌──────────────────────────────────┐                              │
│  │ run_update_automated.py          │                              │
│  │ --env-file .env.production       │                              │
│  └──────────────────────────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  OPTION 3: Update PRODUCTION Database (GitHub Actions)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GitHub Servers                   Production Database               │
│  ┌─────────────────┐              ┌──────────────────┐             │
│  │                 │ connects to  │                  │             │
│  │ GitHub Actions  ├─────────────→│  PostgreSQL      │             │
│  │ Workflow        │ uses GitHub  │  Render/AWS      │             │
│  │ (automated)     │ Secrets      │  (remote server) │             │
│  │                 │              │                  │             │
│  └─────────────────┘              └──────────────────┘             │
│        │                                                            │
│        │ runs                                                       │
│        ↓                                                            │
│  ┌──────────────────────────────────┐                              │
│  │ run_update_automated.py          │                              │
│  │ --env-file .env.production       │                              │
│  │ (created from GitHub Secrets)    │                              │
│  └──────────────────────────────────┘                              │
│                                                                     │
│  ⏰ Scheduled: Mondays 3 AM UTC                                    │
│  🖱️  Manual: Actions tab → Run workflow                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Execution Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXECUTION FLOW                               │
└─────────────────────────────────────────────────────────────────────┘

1️⃣  COMPLETE MODE (Pre-Match)
────────────────────────────────────
   ┌────────────┐
   │  Start     │
   └─────┬──────┘
         │
         ↓
   ┌────────────────────┐
   │ Retrain Weinston   │
   │ (fit model)        │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────────────┐
   │ Generate           │
   │ Predictions        │
   │ (Poisson+Weinston) │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────────────┐
   │ Generate           │
   │ Betting Lines      │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────────────┐
   │ Generate           │
   │ Best Bets          │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────┐
   │   Done     │
   └────────────┘


2️⃣  FINISH MODE (Post-Match)
────────────────────────────────────
   ┌────────────┐
   │  Start     │
   └─────┬──────┘
         │
         ↓
   ┌────────────────────┐
   │ Evaluate           │
   │ Predictions        │
   │ (vs actual results)│
   └─────┬──────────────┘
         │
         ↓
   ┌────────────────────┐
   │ Validate           │
   │ Betting Lines      │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────────────┐
   │ Validate           │
   │ Best Bets          │
   └─────┬──────────────┘
         │
         ↓
   ┌────────────┐
   │   Done     │
   └────────────┘
```

## File Structure

```
55sportsBet/
├── .github/
│   └── workflows/
│       └── update-predictions.yml      ← GitHub Actions workflow
│
├── src/
│   └── scripts/
│       ├── update_predictions.py       ← Original (interactive)
│       └── run_update_automated.py     ← New (automated)
│
├── scripts/
│   └── setup-github-secrets.sh         ← Setup GitHub secrets
│
├── docs/
│   ├── GITHUB_ACTIONS_GUIDE.md         ← GitHub Actions reference
│   ├── LOCAL_EXECUTION_GUIDE.md        ← Local execution guide
│   └── ARCHITECTURE.md                 ← This file
│
├── .env                                 ← LOCAL database config
├── .env.production                      ← PRODUCTION database config
│
├── update-local.bat                     ← Quick script for LOCAL
├── update-prod.bat                      ← Quick script for PRODUCTION
│
├── GITHUB_ACTIONS_SETUP.md             ← Quick start guide
└── AUTOMATION_SUMMARY.md               ← Complete summary
```

## Configuration Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION FILES                             │
└────────────────────────────────────────────────────────────────────┘

LOCAL Database:
───────────────
.env
├── DB_HOST=localhost
├── DB_PORT=5432
├── DB_NAME=local_db
├── DB_USER=postgres
├── DB_PASSWORD=local_password
├── DB_SCHEMA=public
└── API_URL=http://localhost:8000

         ↓ used by

   update-local.bat
   or
   python src/scripts/run_update_automated.py --env-file .env


PRODUCTION Database (Local Execution):
───────────────────────────────────────
.env.production
├── DB_HOST=dpg-xxxxx.render.com
├── DB_PORT=5432
├── DB_NAME=prod_db
├── DB_USER=prod_user
├── DB_PASSWORD=prod_password
├── DB_SCHEMA=public
└── API_URL=https://api.example.com

         ↓ used by

   update-prod.bat
   or
   python src/scripts/run_update_automated.py --env-file .env.production


PRODUCTION Database (GitHub Actions):
──────────────────────────────────────
GitHub Secrets
├── DB_HOST
├── DB_PORT
├── DB_NAME
├── DB_USER
├── DB_PASSWORD
├── DB_SCHEMA
└── API_URL

         ↓ creates

   .env.production (in GitHub Actions runner)

         ↓ used by

   GitHub Actions Workflow
```

## Command Comparison

```
┌────────────────────────────────────────────────────────────────────┐
│                   COMMAND EQUIVALENTS                              │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Interactive (Original)                                          │
├─────────────────────────────────────────────────────────────────┤
│ python src/scripts/update_predictions.py                        │
│ → Asks: Select database? (1=local, 2=prod)                     │
│ → Asks: Select league(s)?                                      │
│ → Asks: Select mode?                                           │
│ → Asks: Enter dates?                                           │
└─────────────────────────────────────────────────────────────────┘

                        ⬇️  EQUIVALENT TO  ⬇️

┌─────────────────────────────────────────────────────────────────┐
│ Automated (Batch Script)                                        │
├─────────────────────────────────────────────────────────────────┤
│ update-local.bat complete 2024-03-11 2024-03-17 all            │
│ → No questions, direct execution                               │
│ → Uses .env automatically                                      │
└─────────────────────────────────────────────────────────────────┘

                        ⬇️  WHICH RUNS  ⬇️

┌─────────────────────────────────────────────────────────────────┐
│ Automated (Python)                                              │
├─────────────────────────────────────────────────────────────────┤
│ python src/scripts/run_update_automated.py \                   │
│   --mode complete \                                             │
│   --date-from 2024-03-11 \                                      │
│   --date-to 2024-03-17 \                                        │
│   --leagues all \                                               │
│   --env-file .env                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Tree: Which Method to Use?

```
                    Need to update database?
                              │
                ┌─────────────┴─────────────┐
                │                           │
          Local Database            Production Database
                │                           │
                ↓                           │
        ┌──────────────┐                   │
        │              │                   │
        │ Use:         │             ┌─────┴──────┐
        │ update-      │             │            │
        │ local.bat    │      Automated?    Manual?
        │              │             │            │
        └──────────────┘             ↓            ↓
                              ┌────────────┐  ┌──────────┐
                              │            │  │          │
                              │ GitHub     │  │ update-  │
                              │ Actions    │  │ prod.bat │
                              │            │  │          │
                              └────────────┘  └──────────┘
```

## Summary

### 3 Ways to Execute

1. **Interactive** (Original)
   - User-friendly
   - Asks questions
   - Choose database interactively

2. **Local Scripts** (New - Easiest)
   - `update-local.bat` for localhost
   - `update-prod.bat` for production
   - No questions, direct execution

3. **GitHub Actions** (New - Automated)
   - Cloud-based
   - Production only
   - Scheduled or manual

### Choose Based On

| Scenario | Use This |
|----------|----------|
| Testing on local DB | `update-local.bat` |
| Manual prod update | `update-prod.bat` or GitHub Actions UI |
| Automatic prod updates | GitHub Actions (scheduled) |
| Need prompts/guidance | Original `update_predictions.py` |

