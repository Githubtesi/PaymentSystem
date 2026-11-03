# src/seedwork/domain/repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional
from .domain_exception import EntityNotFoundError

# T はエンティティの型を表す変数
T = TypeVar('T')
ID = TypeVar("ID")

class IRepository(Generic[T, ID], ABC):
    """
    全リポジトリの基底インターフェース。
    基本的なCRUDのシグネチャを定義する。
    """

    @abstractmethod
    def next_identity(self) -> str:
        """新しいIDを生成して返す（UUIDなど）"""
        pass

    @abstractmethod
    def save(self, entity: T) -> None:
        """エンティティを保存または更新する"""
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """
        IDで検索する。見つからない場合は None を返す。
        (必ず例外を投げたい場合は find_by_id_or_fail を検討)
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> None:
        """指定したIDのデータを削除する"""
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """全件取得する"""
        pass

    def find_by_id_or_fail(self, entity_id: str) -> T:
        """
        IDで検索し、見つからない場合は明示的に EntityNotFoundError を投げる。
        これは共通ロジックとしてここで実装可能。
        """
        entity = self.find_by_id(entity_id)
        if entity is None:
            # クラス名からエンティティ名を推測してエラーを投げる
            raise EntityNotFoundError(entity_id, self.__class__.__name__)
        return entity
