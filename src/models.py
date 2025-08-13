from datetime import date as DateType
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, Date, Float

class Base(DeclarativeBase):
    pass

class League(Base):
    __tablename__ = "leagues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"))

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Anotar con tipo Python (datetime.date) y definir tipo SQLAlchemy en mapped_column
    date: Mapped[DateType] = mapped_column(Date)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    # campos adicionales existentes en tu BD
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fulltime_result: Mapped[str | None] = mapped_column(String(100), nullable=True)
    halftime_homegoal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    halftime_awaygoal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    halftime_result: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referee: Mapped[str | None] = mapped_column(String(100), nullable=True)

class MatchStats(Base):
    __tablename__ = "match_stats"
    # En tu BD match_id es la PK (no existe columna id)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), primary_key=True, index=True)
    # totales/métricas del partido
    total_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cardshome: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cardsaway: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)

class PoissonPrediction(Base):
    __tablename__ = "poisson_predictions"
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"),
        primary_key=True,
        index=True
    )

    prob_home_win: Mapped[float]
    prob_draw: Mapped[float]
    prob_away_win: Mapped[float]
    over_2: Mapped[float]
    under_2: Mapped[float]
    both_score: Mapped[float]

    # 🔽 mapea al nombre real en BD (todo minúsculas)
    both_Noscore: Mapped[float] = mapped_column(name="both_noscore")

    min_odds_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 🔽 idem, mapea a minúsculas
    min_odds_X: Mapped[float | None] = mapped_column(Float, nullable=True, name="min_odds_x")
    min_odds_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_odds_over25: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_odds_under25: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_odds_btts_yes: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_odds_btts_no: Mapped[float | None] = mapped_column(Float, nullable=True)

        # --- NUEVO: goles esperados (como en tu Excel) ---
    expected_home_goals: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_away_goals: Mapped[float | None] = mapped_column(Float, nullable=True)