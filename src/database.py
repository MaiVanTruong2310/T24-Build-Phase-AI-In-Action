import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.config import get_settings

# Lấy cấu hình database URL từ Settings hoặc biến môi trường trực tiếp
settings = get_settings()
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)

# Chuẩn hoá dialect PostgreSQL cho psycopg 3 nếu người dùng dùng postgresql://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Cấu hình engine linh hoạt cho SQLite và PostgreSQL
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

# Khởi tạo SQLAlchemy Engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Khởi tạo Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class cho toàn bộ ORM Models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Database Session cho FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
