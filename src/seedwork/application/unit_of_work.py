from abc import ABC, abstractmethod
from typing import Any, TypeVar, Type

T = TypeVar("T", bound="IUnitOfWork")

class IUnitOfWork(ABC):
    """
    ユニットオブワーク（UoW）のインターフェース。
    複数のリポジトリ操作を一つのトランザクション（原子性）として管理します。
    """

    def __enter__(self: T) -> T:
        """コンテキストを開始します。"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        コンテキストを終了します。
        例外が発生した場合はロールバックし、そうでなければコミットします。
        """
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    @abstractmethod
    def commit(self) -> None:
        """変更を確定させます。通常、ここでイベントの配送も行います。"""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """変更を破棄（ロールバック）します。"""
        pass
