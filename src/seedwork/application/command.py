from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from .dto import DTO
from .result import Result

T_Result = TypeVar("T_Result")
T_Command = TypeVar("T_Command", bound="Command")

@dataclass(frozen=True)
class Command(DTO):
    """
    状態変更の「意図」を表す入力DTO。
    """
    pass

class IUseCase(ABC, Generic[T_Command, T_Result]):
    """
    単一のユースケース（機能）を表すインターフェース。
    """
    @abstractmethod
    def execute(self, command: T_Command) -> Result[T_Result]:
        pass
