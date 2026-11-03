from dataclasses import dataclass

import pytest

from seedwork.domain.versioned_entity import VersionedEntity


@dataclass(eq=False)
class Order(VersionedEntity[str]):
    total: int = 0


def test_version_defaults_to_one():
    assert Order("1", 100).version == 1


def test_version_must_be_positive():
    with pytest.raises(ValueError):
        Order("1", 0, version=0)


def test_increment_version():
    order = Order("1", 100)
    order.increment_version()
    assert order.version == 2


def test_identity_is_still_based_on_id():
    assert Order("1", 100, version=1) == Order("1", 999, version=2)
