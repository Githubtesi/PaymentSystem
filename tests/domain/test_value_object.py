from dataclasses import dataclass

import pytest

from seedwork.domain.domain_exception import ValueObjectValidationError
from seedwork.domain.value_object import ValueObject


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    def validate(self):
        if "@" not in self.value:
            raise ValueObjectValidationError("invalid email")


@dataclass(frozen=True)
class BrokenValue(ValueObject):
    value: str

    def validate(self):
        raise RuntimeError("unexpected")


def test_equal_value_objects_have_equal_values():
    assert Email("a@example.com") == Email("a@example.com")


def test_different_value_objects_are_not_equal():
    assert Email("a@example.com") != Email("b@example.com")


def test_validation_error_is_raised():
    with pytest.raises(ValueObjectValidationError):
        Email("invalid")


def test_unexpected_validation_error_is_wrapped():
    with pytest.raises(ValueObjectValidationError) as exc_info:
        BrokenValue("x")
    assert "unexpected" in str(exc_info.value)
