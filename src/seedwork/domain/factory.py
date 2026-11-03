from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

# 生成するオブジェクトの型
T = TypeVar("T")

class Factory(ABC, Generic[T]):
    """
    ファクトリーの基底クラス。
    複雑なオブジェクトや集約の生成ロジックをカプセル化します。
    """
    @abstractmethod
    def create(self, **kwargs: Any) -> T:
        """
        オブジェクトを生成して返します。
        """
        pass
