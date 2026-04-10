from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ksef2_mcp.adapters.database import orm


def get_engine(db_path: Path | None = None) -> Engine:
    if db_path is None:
        raise ValueError("db_path is required")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", isolation_level="SERIALIZABLE")
    orm.start_mappers()
    orm.metadata.create_all(engine)
    return engine


def get_session_factory(db_path: Path) -> sessionmaker[Session]:
    engine = get_engine(db_path)
    return sessionmaker(bind=engine, expire_on_commit=False)
