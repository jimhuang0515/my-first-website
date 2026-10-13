import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase):
    pass

def now():
    return datetime.now(timezone.utc)

url = os.getenv('DATABASE_URL', 'postgresql+psycopg://stockdev:stockdev@127.0.0.1:5432/stockdev')
if url.startswith('postgres://') or url.startswith('postgresql://'):
    url = 'postgresql+psycopg://' + url.split('://', 1)[1]
engine = create_engine(url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SessionToken(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Stock(Base):
    __tablename__ = 'stocks'
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    exchange: Mapped[str] = mapped_column(String(12))

class WatchlistItem(Base):
    __tablename__ = 'watchlist_items'
    __table_args__ = (UniqueConstraint('user_id', 'symbol'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    symbol: Mapped[str] = mapped_column(ForeignKey('stocks.symbol'))

class AnalysisRun(Base):
    __tablename__ = 'analysis_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    symbol: Mapped[str] = mapped_column(ForeignKey('stocks.symbol'))
    model: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

def get_db():
    with SessionLocal() as db:
        yield db
