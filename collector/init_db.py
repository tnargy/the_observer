"""Initialize the database (create tables)."""
import os

from sqlalchemy import create_engine
from app import Base

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable required")


def init_db():
    """Create database tables using SQLAlchemy metadata."""
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    print(f"Initialized database at {DATABASE_URL}")


if __name__ == '__main__':
    init_db()
