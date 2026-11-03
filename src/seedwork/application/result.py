from dataclasses import dataclass
from typing import Optional, Any, Generic, TypeVar

T = TypeVar('T')

@dataclass(frozen=True)
class Result(Generic[T]):
    """
    ユースケースの実行結果（成功・失敗）を保持する。
    """
    is_success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    code: Optional[str] = None

    @classmethod
    def ok(cls, value: T = None) -> 'Result[T]':
        return cls(is_success=True, value=value)

    @classmethod
    def fail(cls, error: str, code: Optional[str] = None) -> 'Result[T]':
        return cls(is_success=False, error=error, code=code)
