from dataclasses import dataclass, field
from typing import Generic

from .entity import Entity, ID


@dataclass(eq=False)
class VersionedEntity(Entity[ID], Generic[ID]):
    """楽観的ロック用のVersionを持つEntity。"""

    version: int = field(default=1, kw_only=True)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be greater than or equal to 1")

    def increment_version(self) -> None:
        """Domain側で明示的にVersionを進める必要がある場合に利用する。"""
        self.version += 1
