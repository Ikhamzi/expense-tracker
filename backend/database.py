"""Database connection setup.

We use SQLAlchemy to talk to our Neon PostgreSQL database. Neon is just
regular Postgres hosted for us, so nothing here is Neon-specific except
that the connection string happens to point at a neon.tech host.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load variables from a local .env file when running on your own machine.
# On Render, environment variables are set in the dashboard instead, and
# this call is a harmless no-op there.
load_dotenv()

# The Neon connection string, e.g.
# postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
DATABASE_URL = os.environ["DATABASE_URL"]

# The engine manages the pool of connections to the database.
engine = create_engine(DATABASE_URL)

# Each SessionLocal() call gives us a new database session to use for one request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our table models (see models.py) inherit from this Base class.
Base = declarative_base()


def get_db():
    """FastAPI dependency that hands each request its own DB session and
    always closes it afterwards, even if the request raises an error."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
