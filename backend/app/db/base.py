"""
SQLAlchemy declarative base.
Import this wherever models are defined so they all share one metadata object.
All models should also be imported here (at the bottom) so Alembic can discover them.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic autogenerate can discover them.
from app.models import user, project, dataset  # noqa: F401, E402
