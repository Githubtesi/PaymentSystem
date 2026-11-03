from abc import ABC
from dataclasses import dataclass
from typing import Generic, TypeVar

# IDの型（strやUUID、あるいは専用のValueObject）を許容するための型変数
ID = TypeVar("ID")

@dataclass
class Entity(ABC, Generic[ID]):
    """
    全てのエンティティの基底クラス。
    識別子（id）によって同一性を判定する。
    """
    id: ID

    def __eq__(self, other: object) -> bool:
        """
        IDが一致すれば、別のインスタンスでも同一とみなす
        """
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """
        IDを元にハッシュ値を生成し、セットや辞書のキーとして扱えるようにする
        """
        return hash(self.id)
