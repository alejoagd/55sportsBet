@echo off
REM ============================================================================
REM Script para actualizar predicciones en BASE DE DATOS DE PRODUCCION
REM (Ejecutandose desde tu maquina local)
REM ============================================================================
REM
REM Uso:
REM   update-prod.bat complete 2024-03-11 2024-03-17 all
REM   update-prod.bat finish 2024-03-04 2024-03-10 all
REM   update-prod.bat predict 2024-03-11 2024-03-17 "E0,SP1"
REM   update-prod.bat retrain all
REM   update-prod.bat best-bets 2024-03-11 2024-03-17 all
REM
REM ============================================================================

setlocal

REM Verificar si estamos en el directorio correcto
if not exist "src\scripts\run_update_automated.py" (
    echo ERROR: No se encuentra el script. Asegurate de estar en el directorio raiz del proyecto.
    exit /b 1
)

REM Verificar que existe .env.production
if not exist ".env.production" (
    echo ERROR: No se encuentra el archivo .env.production
    echo.
    echo Crea un archivo .env.production con las credenciales de produccion:
    echo   DB_HOST=dpg-xxxxx.render.com
    echo   DB_PORT=5432
    echo   DB_NAME=your_prod_db
    echo   DB_USER=your_user
    echo   DB_PASSWORD=your_password
    echo   DB_SCHEMA=public
    echo   API_URL=https://your-api.onrender.com
    echo.
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
    echo   update-prod.bat ^<mode^> [date_from] [date_to] [leagues]
    echo.
    echo Modos disponibles:
    echo   complete    - Flujo completo pre-partidos ^(requiere fechas^)
    echo   finish      - Flujo completo post-partidos ^(requiere fechas^)
    echo   predict     - Solo predicciones ^(requiere fechas^)
    echo   retrain     - Solo reentrenar modelo
    echo   best-bets   - Solo mejores apuestas ^(requiere fechas^)
    echo.
    echo Ejemplos:
    echo   update-prod.bat complete 2024-03-11 2024-03-17 all
    echo   update-prod.bat finish 2024-03-04 2024-03-10 all
    echo   update-prod.bat retrain all
    echo.
    exit /b 1
)

REM Mostrar advertencia
echo.
echo ============================================================================
echo   ADVERTENCIA: Actualizando BASE DE DATOS DE PRODUCCION
echo ============================================================================
echo.
echo   Esta operacion modificara la base de datos de PRODUCCION.
echo.
set /p CONFIRM=Estas seguro que deseas continuar? (S/N):
if /i not "%CONFIRM%"=="S" (
    echo Operacion cancelada.
    exit /b 0
)

REM Construir comando
set CMD=python src\scripts\run_update_automated.py --mode %MODE% --env-file .env.production

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
echo   Actualizando BASE DE DATOS DE PRODUCCION
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
    echo   COMPLETADO EXITOSAMENTE EN PRODUCCION
    echo ============================================================================
) else (
    echo ============================================================================
    echo   ERROR - Codigo de salida: %EXIT_CODE%
    echo ============================================================================
)

exit /b %EXIT_CODE%
