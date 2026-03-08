@echo off
REM ============================================================================
REM Script para actualizar predicciones en BASE DE DATOS LOCAL
REM ============================================================================
REM
REM Uso:
REM   update-local.bat complete 2024-03-11 2024-03-17 all
REM   update-local.bat finish 2024-03-04 2024-03-10 all
REM   update-local.bat predict 2024-03-11 2024-03-17 "E0,SP1"
REM   update-local.bat retrain all
REM   update-local.bat best-bets 2024-03-11 2024-03-17 all
REM
REM ============================================================================

setlocal

REM Verificar si estamos en el directorio correcto
if not exist "src\scripts\run_update_automated.py" (
    echo ERROR: No se encuentra el script. Asegurate de estar en el directorio raiz del proyecto.
    exit /b 1
)

REM Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call .venv\Scripts\activate.bat
) else (
    echo ADVERTENCIA: No se encontro entorno virtual en .venv
)

REM Obtener parametros
set MODE=%1
set DATE_FROM=%2
set DATE_TO=%3
set LEAGUES=%4

REM Validar modo
if "%MODE%"=="" (
    echo.
    echo ERROR: Debes especificar un modo de operacion
    echo.
    echo Uso:
    echo   update-local.bat ^<mode^> [date_from] [date_to] [leagues]
    echo.
    echo Modos disponibles:
    echo   complete    - Flujo completo pre-partidos ^(requiere fechas^)
    echo   finish      - Flujo completo post-partidos ^(requiere fechas^)
    echo   predict     - Solo predicciones ^(requiere fechas^)
    echo   retrain     - Solo reentrenar modelo
    echo   best-bets   - Solo mejores apuestas ^(requiere fechas^)
    echo.
    echo Ejemplos:
    echo   update-local.bat complete 2024-03-11 2024-03-17 all
    echo   update-local.bat finish 2024-03-04 2024-03-10 all
    echo   update-local.bat retrain all
    echo.
    exit /b 1
)

REM Construir comando
set CMD=python src\scripts\run_update_automated.py --mode %MODE% --env-file .env

REM Agregar fechas si se especificaron
if not "%DATE_FROM%"=="" (
    set CMD=%CMD% --date-from %DATE_FROM%
)

if not "%DATE_TO%"=="" (
    set CMD=%CMD% --date-to %DATE_TO%
)

REM Agregar ligas (default: all)
if "%LEAGUES%"=="" (
    set LEAGUES=all
)
set CMD=%CMD% --leagues %LEAGUES%

REM Mostrar comando
echo.
echo ============================================================================
echo   Actualizando BASE DE DATOS LOCAL
echo ============================================================================
echo   Modo: %MODE%
echo   Fechas: %DATE_FROM% a %DATE_TO%
echo   Ligas: %LEAGUES%
echo ============================================================================
echo.

REM Ejecutar
%CMD%

REM Capturar codigo de salida
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
    echo ============================================================================
    echo   COMPLETADO EXITOSAMENTE
    echo ============================================================================
) else (
    echo ============================================================================
    echo   ERROR - Codigo de salida: %EXIT_CODE%
    echo ============================================================================
)

exit /b %EXIT_CODE%
