from typing import TypeVar, Generic
from abc import ABC, abstractmethod

# 1. 基底となるクラスを定義
class Query(ABC):
    pass

# 2. TypeVar（型変数）を定義
# T_Query は Query クラス（またはそのサブクラス）であることを制約(bound)とする
T_Query = TypeVar('T_Query', bound=Query)
T_Result = TypeVar('T_Result')

# 3. Generic に型変数を渡す
class IQueryHandler(Generic[T_Query, T_Result], ABC):
    @abstractmethod
    def handle(self, query: T_Query) -> T_Result:
        pass
