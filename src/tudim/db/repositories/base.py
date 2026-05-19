from typing import Protocol, runtime_checkable

from tudim.db import models as orm


@runtime_checkable
class Mapper(Protocol):
    """Helper protocol — implementations live next to each repo."""

    @staticmethod
    def to_entity(row): ...
    @staticmethod
    def to_orm(entity): ...
