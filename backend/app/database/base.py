"""
app/database/base.py — Fixed: lazy import inside function to avoid circular imports
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_all_models() -> None:
    from app.models.paper import Paper      # noqa: F401
    from app.models.roadmap import Roadmap  # noqa: F401
