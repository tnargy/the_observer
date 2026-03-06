"""Initialize the database (create tables)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Base
import os

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable required")

def init_db():
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    print(f"Initialized database at {DATABASE_URL}")

if __name__ == '__main__':
    init_db()
