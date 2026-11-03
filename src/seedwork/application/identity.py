from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Identity:
    """
    操作を実行しているユーザーまたはシステムの識別情報を表す値オブジェクト。
    """
    id: str
    name: str
    roles: List[str] = field(default_factory=list)

    @property
    def is_authenticated(self) -> bool:
        """IDが存在すれば認証済みとみなす"""
        return bool(self.id)

    def is_in_role(self, role: str) -> bool:
        """特定のロールを持っているか確認"""
        return role in self.roles


class IIdentityContext(ABC):
    """
    現在の実行コンテキストにおける Identity を取得するためのインターフェース。
    """

    @property
    @abstractmethod
    def current_identity(self) -> Identity:
        """現在の Identity を取得する。"""
        pass
