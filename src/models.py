from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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
    date: Mapped[Date]
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))

class MatchStats(Base):
    __tablename__ = "match_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    home_goals: Mapped[int | None]
    away_goals: Mapped[int | None]
    # agrega campos extra según tu schema real

class PoissonPrediction(Base):
    __tablename__ = "poisson_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    prob_home_win: Mapped[float]
    prob_draw: Mapped[float]
    prob_away_win: Mapped[float]
    over_2: Mapped[float]
    under_2: Mapped[float]
    both_score: Mapped[float]
    both_Noscore: Mapped[float]