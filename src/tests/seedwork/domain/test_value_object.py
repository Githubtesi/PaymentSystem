import pytest
from dataclasses import dataclass  # これが必要です
from seedwork.domain.value_object import ValueObject
from seedwork.domain.domain_exception import ValueObjectValidationError

# @dataclass を付けることで、Quantity(value=-1) のように引数を受け取れるようになります
@dataclass(frozen=True)
class Quantity(ValueObject):
    value: int

    def validate(self) -> None:
        if self.value < 0:
            raise ValueObjectValidationError("数量は0以上である必要があります", "Quantity")

def test_quantity_equality():
    # 同一性のテスト
    assert Quantity(10) == Quantity(10)
    assert Quantity(10) != Quantity(20)

def test_quantity_validation():
    # バリデーションのテスト
    with pytest.raises(ValueObjectValidationError):
        Quantity(-1)