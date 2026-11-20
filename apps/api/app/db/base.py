from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata target for Alembic. Domain models are added in later milestones."""
