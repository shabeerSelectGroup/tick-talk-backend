import enum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def StringEnum(enum_class: type[enum.Enum], *, name: str) -> Enum:
    """Persist str enums by value (e.g. super_admin), not member name (SUPER_ADMIN)."""
    return Enum(
        enum_class,
        values_callable=lambda members: [m.value for m in members],
        name=name,
        native_enum=False,
    )
