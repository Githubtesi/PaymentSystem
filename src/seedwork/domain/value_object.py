# src/seedwork/domain/value_object.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .domain_exception import ValueObjectValidationError # 追加

@dataclass(frozen=True)
class ValueObject(ABC):
    def __post_init__(self):
        try:
            self.validate()
        except Exception as e:
            # 予期せぬエラーも、ValueObjectとしてのエラーにラップして明示する
            if not isinstance(e, ValueObjectValidationError):
                raise ValueObjectValidationError(str(e), self.__class__.__name__)
            raise e

    @abstractmethod
    def validate(self):
        """
        バリデーションロジック。
        失敗した場合は ValueObjectValidationError を raise すること。
        """
        pass


    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ValueObject):
            return False
        return self.__dict__ == other.__dict__
