"""
Sondeo en vivo de resultados desde ESPN (9 ligas).

Hoy los resultados llegan con horas o días de retraso (sudamericanas 2 veces al día, europeas
solo dom-mar vía CSV). Este proceso consulta ESPN con frecuencia solo cuando hay partidos
activos y actualiza el estado en vivo; al terminar un partido pasa el resultado a `matches`,
valida las best bets y regenera los aciertos de ese partido. El sync diario (ESPN y
football-data.org) se mantiene como respaldo y reconciliación: todo es idempotente.

Cadencia: cada --intervalo s (30) si la liga tiene un partido en juego, por empezar (≤30 min)
o recién terminado; cada --reposo s (600) si no. El CDN de ESPN cachea ≤10 s, sondear más
seguido no aporta.

Un resultado solo se da por bueno tras CONFIRMACIONES lecturas seguidas en 'post' y sin estado
de pospuesto/cancelado/suspendido, y se sigue vigilando SEGUIMIENTO_POST s por si ESPN lo corrige.

Uso:
  python -m src.live.poller --dry-run --una-vez      # solo mira y mapea, no escribe
  python -m src.live.poller --dry-run                # observa en vivo sin escribir en la BD
  python -m src.live.poller                          # escribe (solo BD local)
  python -m src.live.poller --ligas "La Liga" "Serie A"

Cada cambio queda en logs/live_poller.jsonl con la hora a la que lo vimos, para medir el
retraso real contra la transmisión. Se niega a escribir en una BD no local sin --allow-remote.
"""
from __future__ import annotations
import argparse
import json
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from src.db import engine
from src.live import store
from src.live.espn_live import SLUGS, LiveEvent, fetch_events
from src.live.matching import encontrar_partido

def pr(*a) -> None:
    """print con flush: en Render stdout no es una terminal y sin esto los logs llegan por bloques."""
    print(*a, flush=True)


CLAVE_CANDADO = 55_000_001   # advisory lock de Postgres: un solo sondeo escribiendo por BD
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}
CONFIRMACIONES = 2
SEGUIMIENTO_POST = 600
VENTANA_PREVIA = 30 * 60
REINTENTO_MAPEO = 300


@dataclass
class Seguimiento:
    match: dict | None = None
    proximo_mapeo: float = 0.0
    firma: tuple | None = None
    jugadas: set = field(default_factory=set)
    confirmaciones: int = 0
    finalizado_en: float | None = None
    sin_mapeo_avisado: bool = False


def firma(ev: LiveEvent) -> tuple:
    return (ev.state, ev.detail, ev.home_score, ev.away_score, ev.home_shootout, ev.away_shootout, len(ev.plays))


def clave_jugada(p: dict) -> tuple:
    return (p.get("type"), p.get("clock"), p.get("team_id"))


class Registro:
    def __init__(self, ruta: Path | None):
        self.f = None
        if ruta is not None:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            self.f = open(ruta, "a", encoding="utf-8")

    def __call__(self, tipo: str, **datos) -> None:
        if self.f is None:
            return
        self.f.write(json.dumps({"t": datetime.now(timezone.utc).isoformat(), "tipo": tipo, **datos},
                                ensure_ascii=False, default=str) + "\n")
        self.f.flush()


def hora() -> str:
    return datetime.now().strftime("%H:%M:%S")


def es_rapido(ev: LiveEvent, s: Seguimiento, ahora: float) -> bool:
    if ev.en_juego:
        return True
    if ev.state == "pre" and ev.kickoff is not None:
        falta = (ev.kickoff - datetime.now(timezone.utc)).total_seconds()
        return -3 * 3600 < falta <= VENTANA_PREVIA          # por empezar o con inicio demorado
    if s.finalizado_en is not None and ahora - s.finalizado_en < SEGUIMIENTO_POST:
        return True
    return ev.tiene_resultado and s.match is not None and s.finalizado_en is None


def procesar_evento(ev: LiveEvent, s: Seguimiento, args, log: Registro, cont: dict) -> None:
    ahora = time.time()
    if s.match is None and ahora >= s.proximo_mapeo:
        with engine.connect() as conn:
            match, motivo = encontrar_partido(conn, ev)
        if match:
            s.match = match
            if not args.dry_run:
                with engine.begin() as conn:
                    store.vincular_evento(conn, match["id"], ev.espn_event_id)
            log("mapeo", liga=ev.league, espn=ev.espn_event_id, match_id=match["id"], motivo=motivo)
        else:
            s.proximo_mapeo = ahora + REINTENTO_MAPEO
            if not s.sin_mapeo_avisado and ev.state != "post":
                pr(f"{hora()} ⚠️  [{ev.league}] sin mapear: {ev.home_name} v {ev.away_name} ({motivo})")
                s.sin_mapeo_avisado = True
                log("sin_mapeo", liga=ev.league, espn=ev.espn_event_id, local=ev.home_name, visita=ev.away_name, motivo=motivo)
    if s.match is None:
        return

    f = firma(ev)
    if f != s.firma:
        previo = s.firma
        nuevas = [p for p in ev.plays if clave_jugada(p) not in s.jugadas]
        s.jugadas.update(clave_jugada(p) for p in ev.plays)
        cont["cambios"] += 1
        # Los partidos por empezar y los ya terminados que vemos por primera vez no se imprimen
        # (siguen quedando en el registro): la consola es para seguir lo que está pasando.
        mostrar = ev.state != "pre" and (previo is not None or ev.state == "in")
        marcador = f"{ev.home_score}-{ev.away_score}" + (f" (pen {ev.home_shootout}-{ev.away_shootout})" if ev.home_shootout is not None else "")
        if mostrar:
            pr(f"{hora()} [{ev.league}] {s.match['home']} {marcador} {s.match['away']} · {ev.detail}")
            if previo and (previo[2], previo[3]) != (ev.home_score, ev.away_score) and ev.state == "in":
                pr(f"{hora()}   ⚽ GOL → {s.match['home']} {ev.home_score}-{ev.away_score} {s.match['away']} ({ev.clock})")
            for p in nuevas:
                icono = "🟥" if p["red"] else ("🟨" if p["yellow"] else ("⚽" if p["scoring"] else "·"))
                pr(f"{hora()}   {icono} {p['type']} {p['clock']}")
        log("cambio", liga=ev.league, match_id=s.match["id"], espn=ev.espn_event_id, estado=ev.state, detalle=ev.detail,
            reloj=ev.clock, marcador=[ev.home_score, ev.away_score], penales=[ev.home_shootout, ev.away_shootout],
            jugadas_nuevas=[{"tipo": p["type"], "min": p["clock"], "clock_s": p.get("clock_s")} for p in nuevas],
            marcador_anterior=list(previo[2:4]) if previo else None)
        if ev.state != "pre" and not args.dry_run:
            with engine.begin() as conn:
                store.guardar_en_vivo(conn, s.match["id"], ev)
        s.firma = f

    if ev.tiene_resultado:
        s.confirmaciones += 1
        if s.confirmaciones >= CONFIRMACIONES:
            _finalizar(ev, s, args, log, cont)
    else:
        s.confirmaciones = 0


def _finalizar(ev: LiveEvent, s: Seguimiento, args, log: Registro, cont: dict) -> None:
    primera = s.finalizado_en is None
    if primera:
        s.finalizado_en = time.time()
    if args.dry_run:
        if primera:
            pr(f"{hora()} ✅ [{ev.league}] FINAL (simulado) {s.match['home']} {ev.home_score}-{ev.away_score} {s.match['away']} · {ev.detail}")
            log("resultado", liga=ev.league, match_id=s.match["id"], accion="simulado", marcador=[ev.home_score, ev.away_score])
        return
    with engine.begin() as conn:
        accion = store.finalizar(conn, s.match, ev)
    if accion == "igual":
        return
    s.match["home_goals"], s.match["away_goals"] = ev.home_score, ev.away_score
    cont["finalizados"] += 1
    outcomes = store.regenerar_aciertos(s.match["id"], s.match["season_id"])
    pr(f"{hora()} ✅ [{ev.league}] RESULTADO {accion.upper()}: {s.match['home']} {ev.home_score}-{ev.away_score} {s.match['away']}"
          f" · {ev.detail} · aciertos {outcomes}")
    log("resultado", liga=ev.league, match_id=s.match["id"], accion=accion, marcador=[ev.home_score, ev.away_score],
        penales=[ev.home_shootout, ev.away_shootout], aciertos=outcomes)


def adquirir_candado():
    """Conexión que retiene un advisory lock de Postgres, o None si otro sondeo ya lo tiene.

    Por qué: en Render un despliegue mantiene un rato vivas la versión vieja y la nueva (y
    alguien puede dejar uno corriendo en su máquina apuntando a la misma BD). Dos sondeos a la
    vez finalizarían y evaluarían el mismo partido dos veces. El lock es de sesión: si el
    proceso muere o se corta la conexión, Postgres lo libera solo.
    """
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    if conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": CLAVE_CANDADO}).scalar():
        return conn
    conn.close()
    return None


def liberar_candado(conn) -> None:
    """Suelta el lock y cierra de verdad la sesión. close() solo devuelve la conexión al pool de
    SQLAlchemy y la sesión de Postgres (con su advisory lock) seguiría viva ahí: otro sondeo no
    podría tomarlo hasta que el pool la descarte."""
    try:
        conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": CLAVE_CANDADO})
    except Exception:
        pass
    try:
        conn.invalidate()
    finally:
        conn.close()


def candado_vigente(conn) -> bool:
    try:
        conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def correr(args, detener: threading.Event) -> dict:
    """Bucle del sondeo. Termina al activarse `detener` (o tras una pasada con --una-vez)."""
    log = Registro(Path(args.log) if args.log else None)
    ligas = args.ligas or list(SLUGS)
    seg: dict[int, Seguimiento] = {}
    proximo = {lg: 0.0 for lg in ligas}
    activa = {lg: False for lg in ligas}   # ¿la liga tuvo partidos activos en la última lectura?
    cont = {"lecturas": 0, "errores": 0, "cambios": 0, "finalizados": 0}
    usa_candado = not args.dry_run and not args.una_vez   # observar no escribe: no necesita candado
    candado = None
    tabla_lista = args.dry_run
    esperando_avisado = False
    try:
        while not detener.is_set():
            if usa_candado and (candado is None or not candado_vigente(candado)):
                if candado is not None:
                    liberar_candado(candado)
                    candado = None
                try:
                    candado = adquirir_candado()
                except Exception as e:
                    pr(f"{hora()} ⚠️  no pude pedir el candado: {str(e)[:80]}")
                if candado is None:
                    if not esperando_avisado:
                        pr(f"{hora()} ⏳ otro sondeo tiene el candado de esta BD; espero (no escribo nada)")
                        esperando_avisado = True
                    detener.wait(30)
                    continue
                esperando_avisado = False
                pr(f"{hora()} 🔒 candado adquirido: este es el único sondeo escribiendo")
            if not tabla_lista:
                with engine.begin() as conn:
                    store.asegurar_tabla(conn)
                tabla_lista = True

            for lg in ligas:
                if time.time() < proximo[lg]:
                    continue
                hoy = datetime.now(timezone.utc)
                # Con partidos activos basta el "día actual" de ESPN (1 llamada). En reposo se pide
                # también ayer (recupera un final que se escapó con el proceso apagado) y mañana
                # (para mapear los partidos que vienen).
                fechas = [None] if activa[lg] else [None, f"{hoy - timedelta(days=1):%Y%m%d}", f"{hoy + timedelta(days=1):%Y%m%d}"]
                try:
                    eventos = fetch_events(lg, fechas=fechas)
                except Exception as e:  # ESPN caído o respuesta rara: se reintenta en el próximo ciclo
                    cont["errores"] += 1
                    pr(f"{hora()} ⚠️  [{lg}] ESPN no respondió: {str(e)[:80]}")
                    log("error", liga=lg, error=str(e)[:200])
                    proximo[lg] = time.time() + args.intervalo
                    continue
                cont["lecturas"] += 1
                rapido = False
                for ev in eventos:
                    s = seg.setdefault(ev.espn_event_id, Seguimiento())
                    try:
                        procesar_evento(ev, s, args, log, cont)
                    except Exception as e:  # un partido con problemas no debe frenar a los demás
                        cont["errores"] += 1
                        pr(f"{hora()} ⚠️  [{lg}] error con {ev.home_name} v {ev.away_name}: {type(e).__name__}: {str(e)[:100]}")
                        log("error", liga=lg, espn=ev.espn_event_id, error=f"{type(e).__name__}: {str(e)[:200]}")
                    rapido = rapido or es_rapido(ev, s, time.time())
                activa[lg] = rapido
                proximo[lg] = time.time() + (args.intervalo if rapido else args.reposo)
            if args.una_vez:
                break
            detener.wait(max(1.0, min(proximo.values()) - time.time()))
    finally:
        if candado is not None:
            liberar_candado(candado)
    return cont


class SondeoEnSegundoPlano:
    """Corre el sondeo como hilo dentro del API (ver lifespan en src/api.py)."""

    def __init__(self, dry_run: bool):
        self._detener = threading.Event()
        # allow_remote=True a propósito: en Render la BD nunca es local, y arrancar esto ya
        # exige haber puesto LIVE_POLLER=on (o dry) a mano en el servicio.
        self._args = SimpleNamespace(ligas=None, intervalo=30, reposo=600, una_vez=False,
                                     dry_run=dry_run, allow_remote=True, log=None)
        self._hilo = threading.Thread(target=self._correr, name="sondeo-en-vivo", daemon=True)
        self._hilo.start()

    def _correr(self) -> None:
        pr(f"{hora()} sondeo en vivo iniciado en segundo plano · {'OBSERVACIÓN (no escribe)' if self._args.dry_run else 'ESCRIBE'}")
        while not self._detener.is_set():
            try:
                correr(self._args, self._detener)
                return
            except Exception as e:  # un fallo del sondeo jamás debe afectar al API
                pr(f"{hora()} ⚠️  el sondeo falló ({type(e).__name__}: {str(e)[:120]}); reintento en 60 s")
                self._detener.wait(60)

    def detener(self) -> None:
        self._detener.set()
        self._hilo.join(timeout=10)


def iniciar_en_segundo_plano(dry_run: bool) -> SondeoEnSegundoPlano:
    return SondeoEnSegundoPlano(dry_run)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ligas", nargs="+", choices=list(SLUGS), help="Solo estas ligas (por defecto las 9)")
    ap.add_argument("--intervalo", type=int, default=30, help="Segundos entre lecturas con partidos activos")
    ap.add_argument("--reposo", type=int, default=600, help="Segundos entre lecturas sin partidos activos")
    ap.add_argument("--una-vez", action="store_true", help="Una lectura de cada liga y termina")
    ap.add_argument("--dry-run", action="store_true", help="Observa y mapea, no escribe en la BD")
    ap.add_argument("--allow-remote", action="store_true", help="Permite escribir en una BD no local")
    ap.add_argument("--log", default="logs/live_poller.jsonl")
    args = ap.parse_args()

    host = engine.url.host
    if not args.dry_run and host not in LOCAL_HOSTS and not args.allow_remote:
        pr(f"⛔ La BD configurada es '{host}' (no local). Abortado: usa --dry-run o --allow-remote.")
        return 2
    pr(f"BD: {host or 'socket local'}/{engine.url.database} · {'SIMULACIÓN (no escribe)' if args.dry_run else 'ESCRIBE'}"
       f" · cada {args.intervalo}s con partidos activos, {args.reposo}s en reposo · Ctrl-C para terminar")
    detener = threading.Event()
    try:
        cont = correr(args, detener)
    except KeyboardInterrupt:
        detener.set()
        cont = {"lecturas": 0, "cambios": 0, "finalizados": 0, "errores": 0}
    pr(f"\nResumen: {cont['lecturas']} lecturas · {cont['cambios']} cambios · {cont['finalizados']} resultados guardados · {cont['errores']} errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
