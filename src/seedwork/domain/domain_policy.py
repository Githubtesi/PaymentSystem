from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

T = TypeVar("T")
R = TypeVar("R")

class DomainPolicy(ABC, Generic[T, R]):
    """
    ドメインポリシー（戦略）の基底クラス。
    特定の入力(T)に対して、業務ルールに基づいた結果(R)を算出します。
    
    例:
    - 割引ポリシー: 注文内容から割引額を算出
    - 配送ポリシー: 配送先から送料を算出
    """
    @abstractmethod
    def apply(self, domain_object: T) -> R:
        """
        ポリシーを適用して結果を返します。
        """
        pass
