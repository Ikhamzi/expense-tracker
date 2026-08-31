"""Database connection setup.

We use SQLAlchemy to talk to our Neon PostgreSQL database. Neon is just
regular Postgres hosted for us, so nothing here is Neon-specific except
that the connection string happens to point at a neon.tech host.

This is the same engine/session setup the old top-level database.py had,
with one addition: explicit connection pool settings tuned for Render's
free tier talking to Neon's free tier (see the comments below).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from infrastructure.config import settings

# The engine manages the pool of connections to the database.
#
# Pool tuning, explained for a beginner:
# - pool_size=5: keep up to 5 connections open and ready to reuse. Render's
#   free web service plan and Neon's free tier both have limited resources,
#   so we don't want to open a huge number of idle connections.
# - max_overflow=5: if all 5 pooled connections are busy, allow up to 5 more
#   temporary ones rather than making requests wait or fail outright.
# - pool_pre_ping=True: before handing out a pooled connection, SQLAlchemy
#   sends a cheap "are you still there?" check first. Neon (and Render)
#   can silently close idle connections; without this, the next query on a
#   dead connection would fail with a confusing error instead of SQLAlchemy
#   quietly reconnecting.
# - pool_recycle=300: discard and reopen any connection older than 300
#   seconds (5 minutes), for the same reason - it avoids handing out a
#   connection that the database has already dropped.
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Each SessionLocal() call gives us a new database session to use for one request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our table models (see infrastructure/db/models.py) inherit from this
# Base class. Alembic's migrations (see alembic/env.py) also read this
# Base's metadata to know what tables should exist.
Base = declarative_base()


def get_db():
    """FastAPI dependency that hands each request its own DB session and
    always closes it afterwards, even if the request raises an error."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
