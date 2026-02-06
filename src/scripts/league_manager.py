# src/scripts/league_manager.py
"""
Gestor de ligas para scripts de automatización.
Proporciona selección interactiva y configuración multi-liga.
"""

from sqlalchemy import text
from typing import List, Dict, Optional, Tuple
from src.predictions.league_context import LeagueContext

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


class LeagueConfig:
    """Configuración de una liga para procesamiento"""
    
    def __init__(self, league_id: int, league_name: str, country: str, 
                 season_id: int, season_year: str, 
                 csv_code: str, dayfirst: bool = True):
        self.league_id = league_id
        self.league_name = league_name
        self.country = country
        self.season_id = season_id
        self.season_year = season_year
        self.csv_code = csv_code  # E0, SP1, I1, etc.
        self.dayfirst = dayfirst
    
    def __str__(self):
        flag = self.get_flag()
        return f"{flag} {self.league_name} ({self.season_year}) - Season ID: {self.season_id}"
    
    def get_flag(self) -> str:
        """Mapea país a emoji de bandera"""
        flags = {
            "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
            "Spain": "🇪🇸",
            "Italy": "🇮🇹",
            "Germany": "🇩🇪",
            "France": "🇫🇷",
            "Brazil": "🇧🇷",
            "Argentina": "🇦🇷",
            "Colombia": "🇨🇴",
        }
        return flags.get(self.country, "⚽")
    
    def get_csv_path(self, data_dir: str = "dat/raw") -> str:
        """Retorna path típico del CSV para esta liga"""
        return f"{data_dir}/{"fixtures_"+self.csv_code}.csv"


class LeagueManager:
    """Gestiona la selección y configuración de ligas"""
    
    # Mapeo de ligas a códigos CSV de football-data.co.uk
    LEAGUE_CSV_MAPPING = {
        "Premier League": ("E0", True),    # England, dayfirst=True
        "La Liga": ("SP1", True),          # Spain, dayfirst=True
        "Serie A": ("I1", True),           # Italy, dayfirst=True
        "Bundesliga": ("D1", True),        # Germany, dayfirst=True
        "Ligue 1": ("F1", True),           # France, dayfirst=True
        "Brasileirao": ("BR", False),      # Brazil, dayfirst=False
        "Liga Argentina": ("AR", False),   # Argentina, dayfirst=False
        "Liga Betplay": ("CO", False),     # Colombia, dayfirst=False
    }
    
    def __init__(self, conn):
        self.conn = conn
        self.available_leagues = self._load_available_leagues()
    
    def _load_available_leagues(self) -> List[LeagueConfig]:
        """Carga ligas con datos activos y sus configuraciones"""
        query = text("""
            SELECT 
                l.id as league_id,
                l.name as league_name,
                l.country,
                s.id as season_id,
                s.year_start || '/' || s.year_end as season_year,
                COUNT(DISTINCT m.id) as total_matches,
                COUNT(DISTINCT CASE WHEN m.home_goals IS NULL THEN m.id END) as upcoming_matches,
                COUNT(DISTINCT CASE WHEN m.home_goals IS NOT NULL THEN m.id END) as finished_matches
            FROM leagues l
            JOIN seasons s ON s.league_id = l.id
            LEFT JOIN matches m ON m.season_id = s.id
            WHERE s.year_start = (
                SELECT MAX(year_start) FROM seasons WHERE league_id = l.id
            )
            GROUP BY l.id, l.name, l.country, s.id, s.year_start, s.year_end
            HAVING COUNT(DISTINCT m.id) > 0
            ORDER BY l.name
        """)
        
        rows = self.conn.execute(query).mappings().all()
        
        configs = []
        for row in rows:
            # Obtener configuración CSV
            csv_code, dayfirst = self.LEAGUE_CSV_MAPPING.get(
                row['league_name'], 
                ("UNKNOWN", True)
            )
            
            config = LeagueConfig(
                league_id=row['league_id'],
                league_name=row['league_name'],
                country=row['country'],
                season_id=row['season_id'],
                season_year=row['season_year'],
                csv_code=csv_code,
                dayfirst=dayfirst
            )
            
            # Agregar info de partidos para mostrar
            config.total_matches = row['total_matches']
            config.upcoming_matches = row['upcoming_matches']
            config.finished_matches = row['finished_matches']
            
            configs.append(config)
        
        return configs
    
    def display_available_leagues(self):
        """Muestra ligas disponibles con formato colorido"""
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}  LIGAS DISPONIBLES{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        for idx, config in enumerate(self.available_leagues, 1):
            print(f"  {Colors.BOLD}{idx}.{Colors.END} {config}")
            print(f"     {Colors.BLUE}CSV:{Colors.END} {config.csv_code}.csv  "
                  f"{Colors.BLUE}|{Colors.END}  "
                  f"{Colors.GREEN}Terminados:{Colors.END} {config.finished_matches}  "
                  f"{Colors.YELLOW}Futuros:{Colors.END} {config.upcoming_matches}")
        
        print(f"\n  {Colors.BOLD}{len(self.available_leagues) + 1}.{Colors.END} "
              f"⚽  {Colors.BOLD}TODAS{Colors.END} las ligas activas\n")
    
    def select_leagues(self, prompt: str = "Selecciona liga(s)") -> List[LeagueConfig]:
        """
        Selección interactiva de ligas.
        
        Returns:
            Lista de LeagueConfig seleccionados
        """
        self.display_available_leagues()
        
        while True:
            selection = input(
                f"{Colors.GREEN}{prompt} [1,2 o 'all']: {Colors.END}"
            ).strip().lower()
            
            if selection == 'all':
                print(f"{Colors.YELLOW}✓ Seleccionadas TODAS las ligas{Colors.END}")
                return self.available_leagues.copy()
            
            try:
                indices = [int(x.strip()) for x in selection.split(',')]
                selected = []
                
                for idx in indices:
                    if 1 <= idx <= len(self.available_leagues):
                        selected.append(self.available_leagues[idx-1])
                    else:
                        print(f"{Colors.RED}❌ Opción {idx} inválida{Colors.END}")
                        break
                else:
                    if selected:
                        print(f"{Colors.GREEN}✓ Seleccionadas: {', '.join(c.league_name for c in selected)}{Colors.END}")
                        return selected
                    else:
                        print(f"{Colors.RED}❌ Debes seleccionar al menos una liga{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}❌ Formato inválido. Usa números separados por comas (ej: 1,2){Colors.END}")
    
    def get_league_by_season_id(self, season_id: int) -> Optional[LeagueConfig]:
        """Obtiene configuración de liga por season_id"""
        for config in self.available_leagues:
            if config.season_id == season_id:
                return config
        return None
    
    def confirm_multi_league_operation(self, selected: List[LeagueConfig], operation: str) -> bool:
        """Confirma operación multi-liga con el usuario"""
        print(f"\n{Colors.YELLOW}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}  CONFIRMACIÓN: {operation.upper()}{Colors.END}")
        print(f"{Colors.YELLOW}{'='*70}{Colors.END}\n")
        
        print(f"  Se procesarán {Colors.BOLD}{len(selected)}{Colors.END} liga(s):\n")
        for config in selected:
            print(f"    • {config}")
        
        response = input(
            f"\n{Colors.YELLOW}¿Continuar con esta operación? (s/n): {Colors.END}"
        ).strip().lower()
        
        return response == 's'


def print_league_header(config: LeagueConfig, step_num: int = None, total_steps: int = None):
    """Imprime header colorido para una liga"""
    if step_num and total_steps:
        progress = f" [{step_num}/{total_steps}]"
    else:
        progress = ""
    
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}  {config.get_flag()} {config.league_name} ({config.season_year}){progress}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")


# Ejemplo de uso
if __name__ == "__main__":
    from src.db import engine
    
    with engine.begin() as conn:
        manager = LeagueManager(conn)
        
        print("\n=== DEMO: League Manager ===\n")
        
        # Mostrar ligas
        manager.display_available_leagues()
        
        # Seleccionar
        selected = manager.select_leagues()
        
        print(f"\n✓ Seleccionaste {len(selected)} liga(s):")
        for config in selected:
            print(f"  - {config}")
            print(f"    CSV: {config.get_csv_path()}")