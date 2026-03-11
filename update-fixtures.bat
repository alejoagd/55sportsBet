@echo off
REM ============================================================
REM Update Fixtures Script - LOCAL EXECUTION
REM Downloads upcoming fixtures from football-data.org (FREE)
REM ============================================================

echo.
echo ============================================================
echo   UPDATE FIXTURES - LOCAL
echo   Using football-data.org API (FREE)
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if API key is configured
if not defined FOOTBALL_DATA_ORG_KEY (
    echo WARNING: FOOTBALL_DATA_ORG_KEY not set in environment
    echo.
    echo Please add to your .env file:
    echo FOOTBALL_DATA_ORG_KEY=your_key_here
    echo.
    echo Get FREE API key at:
    echo https://www.football-data.org/client/register
    echo.
    pause
    exit /b 1
)

REM Download fixtures for all leagues
echo Downloading upcoming fixtures from football-data.org...
echo.
python scripts/download-fixtures-final.py --leagues all --output data

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   ERROR: Fixture download failed
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SUCCESS: Fixtures downloaded
echo ============================================================
echo.
echo Files created:
echo   - data/fixtures_E0.csv (Premier League)
echo   - data/fixtures_SP1.csv (La Liga)
echo   - data/fixtures_D1.csv (Bundesliga)
echo   - data/fixtures_I1.csv (Serie A)
echo.
echo Next steps:
echo   1. Check CSV files have correct format (date;home;away)
echo   2. Run update-local.bat to update database
echo.
pause
