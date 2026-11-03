from dataclasses import dataclass

from seedwork.domain.entity import Entity


@dataclass(eq=False)
class User(Entity[str]):
    name: str = ""


@dataclass(eq=False)
class Product(Entity[str]):
    name: str = ""


def test_entities_with_same_id_are_equal():
    assert User("1", "Alice") == User("1", "Bob")


def test_entities_with_different_ids_are_not_equal():
    assert User("1", "Alice") != User("2", "Alice")


def test_entity_hash_is_based_on_id():
    assert hash(User("1", "Alice")) == hash(User("1", "Bob"))


def test_different_entity_types_with_same_id_are_currently_equal():
    assert User("1", "Alice") == Product("1", "Book")
