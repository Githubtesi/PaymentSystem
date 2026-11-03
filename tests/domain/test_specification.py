from seedwork.domain.specification import Specification


class GreaterThanTen(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate > 10


class Even(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate % 2 == 0


def test_and_specification():
    spec = GreaterThanTen() & Even()
    assert spec.is_satisfied_by(12)
    assert not spec.is_satisfied_by(11)


def test_or_specification():
    spec = GreaterThanTen() | Even()
    assert spec.is_satisfied_by(12)
    assert spec.is_satisfied_by(8)
    assert not spec.is_satisfied_by(7)


def test_not_specification():
    spec = ~GreaterThanTen()
    assert spec.is_satisfied_by(10)
    assert not spec.is_satisfied_by(11)
