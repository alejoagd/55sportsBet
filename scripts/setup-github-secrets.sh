#!/bin/bash

# Script para configurar los secrets de GitHub Actions
# Requiere GitHub CLI instalado: https://cli.github.com/

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     GitHub Actions Secrets Setup - 55sportsBet            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que gh está instalado
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI no está instalado"
    echo "ℹ️  Instala GitHub CLI desde: https://cli.github.com/"
    exit 1
fi

# Verificar que el usuario está autenticado
if ! gh auth status &> /dev/null; then
    echo "❌ Error: No estás autenticado en GitHub CLI"
    echo "ℹ️  Ejecuta: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI instalado y autenticado"
echo ""

# Función para pedir un valor de forma segura
ask_secret() {
    local var_name=$1
    local description=$2
    local current_value=$3

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 $var_name"
    echo "   $description"

    if [ -n "$current_value" ]; then
        echo "   Valor actual en .env: $current_value"
    fi

    read -p "   Ingresa el valor (Enter para saltar): " value

    if [ -n "$value" ]; then
        echo "   ⏳ Guardando secret..."
        gh secret set "$var_name" --body "$value"
        echo "   ✅ Secret guardado exitosamente"
    else
        echo "   ⏭️  Omitido"
    fi
    echo ""
}

echo "Configurando secrets desde archivo .env.production..."
echo ""

# Cargar valores desde .env.production si existe
ENV_FILE=".env.production"

if [ -f "$ENV_FILE" ]; then
    echo "✅ Archivo $ENV_FILE encontrado"
    source "$ENV_FILE"
else
    echo "⚠️  Archivo $ENV_FILE no encontrado"
    echo "ℹ️  Los valores deberán ingresarse manualmente"
fi

echo ""
echo "A continuación, configura cada secret de GitHub Actions:"
echo "(Presiona Enter para saltar un valor si no quieres actualizarlo)"
echo ""

# Configurar cada secret
ask_secret "DB_HOST" "Host del servidor PostgreSQL" "$DB_HOST"
ask_secret "DB_PORT" "Puerto del servidor PostgreSQL (usualmente 5432)" "${DB_PORT:-5432}"
ask_secret "DB_NAME" "Nombre de la base de datos" "$DB_NAME"
ask_secret "DB_USER" "Usuario de la base de datos" "$DB_USER"
ask_secret "DB_PASSWORD" "Contraseña de la base de datos" "$DB_PASSWORD"
ask_secret "DB_SCHEMA" "Schema de la base de datos (usualmente 'public')" "${DB_SCHEMA:-public}"
ask_secret "API_URL" "URL de tu API (ej: https://api.example.com)" "$API_URL"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Configuración completada!"
echo ""
echo "📋 Siguiente paso:"
echo "   1. Ve a la pestaña 'Actions' en GitHub"
echo "   2. Selecciona el workflow 'Update Predictions'"
echo "   3. Haz clic en 'Run workflow'"
echo "   4. Configura los parámetros y ejecuta"
echo ""
echo "📖 Lee la documentación completa en: docs/GITHUB_ACTIONS_GUIDE.md"
echo ""
