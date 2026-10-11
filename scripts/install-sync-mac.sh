#!/usr/bin/env bash
# Instala (o quita) la tarea programada de macOS que ejecuta
# sync-local-from-prod.sh solo, para mantener la base local al día.
#
#   ./scripts/install-sync-mac.sh              instalar
#   ./scripts/install-sync-mac.sh --status     ver si está activa y el último log
#   ./scripts/install-sync-mac.sh --uninstall  quitar la tarea
#
# Horario: domingo a miércoles a las 17:00 hora local, un rato después de que
# el workflow update-predictions.yml (GitHub Actions) carga resultados en
# producción. Para cambiarlo, edita HORAS/DIAS abajo y vuelve a instalar.
#
# Por qué se COPIA el script y las credenciales fuera del repo: el repo suele
# estar en ~/Documents, y macOS (TCC) le niega a las tareas de launchd leer esa
# carpeta sin darle "Acceso total al disco" a /bin/bash. Copiando el script y
# la DATABASE_URL a ~/Library/Application Support (con permisos 600) la tarea
# no necesita tocar Documents. Si cambias el script o la URL, reinstala.
set -euo pipefail

LABEL="com.55sportsbet.sync-local-db"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_DIR="$HOME/Library/Application Support/55sportsBet"
LOG="$HOME/Library/Logs/55sportsbet-sync.log"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="gui/$(id -u)"

HORA=17
MINUTO=0
DIAS="0 1 2 3"   # 0=domingo, 1=lunes, 2=martes, 3=miércoles

case "${1:-}" in
  --uninstall)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    rm -rf "$APP_DIR"
    echo "Tarea eliminada (el log queda en $LOG)."
    exit 0 ;;
  --status)
    if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then echo "Tarea ACTIVA ($LABEL)."; else echo "Tarea NO instalada."; fi
    [ -f "$LOG" ] && { echo "--- últimas líneas de $LOG"; tail -n 8 "$LOG"; } || echo "Sin log todavía."
    exit 0 ;;
  "") ;;
  *) echo "Uso: $0 [--status|--uninstall]"; exit 1 ;;
esac

ENV_FILE="$REPO_DIR/.env.production"
[ -f "$ENV_FILE" ] || { echo "Falta $ENV_FILE (pídelo al mantenedor)."; exit 1; }
URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
[ -n "$URL" ] || { echo "$ENV_FILE no tiene DATABASE_URL."; exit 1; }

mkdir -p "$APP_DIR" "$HOME/Library/LaunchAgents" "$(dirname "$LOG")"
cp "$REPO_DIR/scripts/sync-local-from-prod.sh" "$APP_DIR/sync-local-from-prod.sh"
chmod 755 "$APP_DIR/sync-local-from-prod.sh"
( umask 077; printf 'DATABASE_URL=%s\n' "$URL" > "$APP_DIR/prod.env" )

INTERVALS=""
for d in $DIAS; do
  INTERVALS+="    <dict><key>Weekday</key><integer>$d</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>$MINUTO</integer></dict>
"
done

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$APP_DIR/sync-local-from-prod.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PROD_ENV_FILE</key><string>$APP_DIR/prod.env</string></dict>
  <key>StartCalendarInterval</key>
  <array>
$INTERVALS  </array>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"

echo "Tarea instalada: domingo a miércoles a las $(printf '%02d:%02d' $HORA $MINUTO) (hora local)."
echo "  Probarla ahora:  launchctl kickstart $DOMAIN/$LABEL"
echo "  Ver estado/log:  $0 --status"
echo "  Quitarla:        $0 --uninstall"
