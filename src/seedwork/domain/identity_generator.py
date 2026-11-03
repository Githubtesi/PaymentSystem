from abc import ABC, abstractmethod
from typing import Generic, TypeVar

ID = TypeVar("ID")

class IIdentityGenerator(ABC, Generic[ID]):
    """
    ID生成器のインターフェース。
    ビジネスルールに基づいたID（採番）が必要な場合に使用します。
    """
    @abstractmethod
    def next_identity(self) -> ID:
        """
        次の一意な識別子を生成して返します。
        """
        pass
