# GitHub Actions - Automated Predictions Pipeline

This guide explains how to use the automated GitHub Actions workflow to execute prediction updates for your sports betting platform.

## Overview

The `update-predictions.yml` workflow automates the execution of the prediction update process, which includes:

- Loading fixtures
- Training models (Poisson & Weinston)
- Generating predictions
- Creating betting lines
- Generating and validating best bets

## Features

### 1. **Manual Trigger**
Execute the workflow manually from GitHub's web interface with custom parameters.

### 2. **Scheduled Execution**
Automatically runs every Monday at 3 AM UTC (can be customized).

### 3. **Multiple Operation Modes**
- `complete`: Full pre-match workflow (RETRAIN → PREDICT → BETTING LINES → BEST BETS)
- `finish`: Full post-match workflow (EVALUATE → VALIDATE BETTING → VALIDATE BEST BETS)
- `predict`: Generate predictions only
- `retrain`: Retrain Weinston model only
- `best-bets`: Generate best bets only

### 4. **Multi-League Support**
Process all leagues or select specific ones (E0, SP1, D1, I1, etc.)

## Setup

### Required GitHub Secrets

You need to configure the following secrets in your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `dpg-xxxxx.render.com` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `sportsbet_db` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | `your-secure-password` |
| `DB_SCHEMA` | Database schema | `public` |
| `API_URL` | Your API URL | `https://your-api.onrender.com` |

### How to Add Secrets

```bash
# Via GitHub CLI
gh secret set DB_HOST --body "your-db-host"
gh secret set DB_PORT --body "5432"
gh secret set DB_NAME --body "your-db-name"
gh secret set DB_USER --body "your-db-user"
gh secret set DB_PASSWORD --body "your-password"
gh secret set DB_SCHEMA --body "public"
gh secret set API_URL --body "https://your-api.onrender.com"
```

Or manually through GitHub web interface:
1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Enter name and value
4. Click **Add secret**

## Usage

### Manual Execution

#### Via GitHub Web Interface

1. Go to **Actions** tab in your repository
2. Select **Update Predictions** workflow
3. Click **Run workflow**
4. Fill in the parameters:
   - **Operation mode**: Select the desired mode
   - **Date from**: Start date (YYYY-MM-DD)
   - **Date to**: End date (YYYY-MM-DD)
   - **Leagues**: `all` or specific codes like `E0,SP1,D1,I1`
5. Click **Run workflow**

#### Via GitHub CLI

```bash
# Complete flow for all leagues (next week)
gh workflow run update-predictions.yml \
  -f operation_mode=complete \
  -f date_from=2024-01-15 \
  -f date_to=2024-01-21 \
  -f leagues=all

# Predict only for Premier League and La Liga
gh workflow run update-predictions.yml \
  -f operation_mode=predict \
  -f date_from=2024-01-15 \
  -f date_to=2024-01-21 \
  -f leagues="E0,SP1"

# Finish flow (post-match) for all leagues
gh workflow run update-predictions.yml \
  -f operation_mode=finish \
  -f date_from=2024-01-08 \
  -f date_to=2024-01-14 \
  -f leagues=all

# Retrain models for all leagues
gh workflow run update-predictions.yml \
  -f operation_mode=retrain \
  -f leagues=all

# Generate best bets only
gh workflow run update-predictions.yml \
  -f operation_mode=best-bets \
  -f date_from=2024-01-15 \
  -f date_to=2024-01-21 \
  -f leagues=all
```

### Scheduled Execution

The workflow runs automatically every Monday at 3 AM UTC. You can customize this by editing the cron expression in `.github/workflows/update-predictions.yml`:

```yaml
schedule:
  - cron: '0 3 * * 1'  # Mondays at 3 AM UTC
  # Examples:
  # - cron: '0 0 * * *'    # Daily at midnight
  # - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 8 * * 1,5'  # Mondays and Fridays at 8 AM
```

## Operation Modes Explained

### 1. Complete Mode (`complete`)

**Purpose**: Pre-match preparation for upcoming fixtures.

**Steps**:
1. Retrain Weinston model with latest results
2. Generate predictions for upcoming matches
3. Create betting lines
4. Generate best bets recommendations

**When to use**: Before the start of a new matchweek.

**Example**:
```bash
gh workflow run update-predictions.yml \
  -f operation_mode=complete \
  -f date_from=2024-01-15 \
  -f date_to=2024-01-21 \
  -f leagues=all
```

### 2. Finish Mode (`finish`)

**Purpose**: Post-match analysis and validation.

**Steps**:
1. Evaluate predictions against actual results
2. Validate betting line recommendations
3. Validate best bets outcomes

**When to use**: After matches are completed.

**Example**:
```bash
gh workflow run update-predictions.yml \
  -f operation_mode=finish \
  -f date_from=2024-01-08 \
  -f date_to=2024-01-14 \
  -f leagues=all
```

### 3. Predict Mode (`predict`)

**Purpose**: Generate predictions only.

**Steps**:
1. Generate Poisson predictions
2. Generate Weinston predictions

**When to use**: When you only need to update predictions without full pipeline.

### 4. Retrain Mode (`retrain`)

**Purpose**: Retrain Weinston model with latest data.

**Steps**:
1. Retrain Weinston model parameters

**When to use**: When new results are available and you want to update model parameters.

### 5. Best Bets Mode (`best-bets`)

**Purpose**: Generate best betting opportunities.

**Steps**:
1. Analyze all predictions
2. Generate top betting recommendations

**When to use**: When you want fresh best bets based on existing predictions.

## League Codes

| Code | League |
|------|--------|
| `E0` | English Premier League |
| `SP1` | Spanish La Liga |
| `D1` | German Bundesliga |
| `I1` | Italian Serie A |

Use `all` to process all available leagues, or specify codes separated by commas: `E0,SP1,D1,I1`

## Monitoring and Logs

### View Workflow Runs

1. Go to **Actions** tab
2. Click on the workflow run
3. View the execution details and logs

### Download Logs

After each run, logs are automatically uploaded as artifacts and retained for 30 days.

1. Go to the completed workflow run
2. Scroll to **Artifacts** section
3. Download `prediction-update-logs-{run_number}`

### Check for Failures

The workflow will:
- Mark as ❌ **failed** if any critical error occurs
- Display error messages in the logs
- Upload logs even on failure (for debugging)

## Troubleshooting

### Database Connection Errors

**Error**: `Error al conectar a la base de datos`

**Solutions**:
1. Verify database secrets are correctly set
2. Check if database is accessible from GitHub Actions
3. Verify `DB_PASSWORD` secret is correct
4. Check database server is running

### API Connection Errors

**Error**: `No se pudo conectar a la API`

**Solutions**:
1. Verify `API_URL` secret is set correctly
2. Check if API server is running
3. Verify API is accessible from GitHub Actions
4. Check API endpoints are available

### Missing Leagues

**Error**: `Liga no encontrada`

**Solutions**:
1. Verify league codes are correct (E0, SP1, D1, I1)
2. Check leagues exist in database
3. Use `all` to process all available leagues

### Date Format Errors

**Error**: `Formato de fecha inválido`

**Solutions**:
1. Use correct format: `YYYY-MM-DD`
2. Example: `2024-01-15`

## Local Testing

Before running in GitHub Actions, you can test the automated script locally:

```bash
# Set environment file
export ENV_FILE=.env.production

# Test complete flow
python src/scripts/run_update_automated.py \
  --mode complete \
  --date-from 2024-01-15 \
  --date-to 2024-01-21 \
  --leagues all \
  --env-file .env.production

# Test with specific leagues
python src/scripts/run_update_automated.py \
  --mode predict \
  --date-from 2024-01-15 \
  --date-to 2024-01-21 \
  --leagues "E0,SP1" \
  --env-file .env

# Test retrain
python src/scripts/run_update_automated.py \
  --mode retrain \
  --leagues all \
  --env-file .env
```

## Best Practices

1. **Schedule Wisely**: Schedule the `complete` mode before matchweeks start and `finish` mode after they end.

2. **Test First**: Use manual triggers to test before relying on scheduled runs.

3. **Monitor Logs**: Regularly check workflow logs to catch issues early.

4. **Keep Secrets Updated**: Update secrets when database credentials change.

5. **Use Date Ranges**: Be specific with date ranges to avoid processing unnecessary data.

6. **Gradual Rollout**: Start with single league testing before processing all leagues.

## Advanced Configuration

### Custom Cron Schedules

```yaml
# Run twice weekly (Monday and Thursday at 2 AM)
schedule:
  - cron: '0 2 * * 1,4'

# Run daily at specific times
schedule:
  - cron: '0 1 * * *'  # 1 AM - Complete flow
  - cron: '0 23 * * *' # 11 PM - Finish flow
```

### Workflow Chaining

Trigger this workflow from another workflow:

```yaml
- name: Trigger prediction update
  run: |
    gh workflow run update-predictions.yml \
      -f operation_mode=complete \
      -f date_from=$(date -d '+1 day' +%Y-%m-%d) \
      -f date_to=$(date -d '+7 days' +%Y-%m-%d) \
      -f leagues=all
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Support

For issues or questions:
1. Check workflow logs in Actions tab
2. Review this documentation
3. Contact the development team
4. Open an issue in the repository

## Changelog

### Version 1.0.0 (Initial Release)
- ✅ Manual trigger support
- ✅ Scheduled execution (weekly)
- ✅ Five operation modes
- ✅ Multi-league support
- ✅ Automated logging
- ✅ Error handling and notifications
