from dataclasses import dataclass

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from seedwork.domain.entity import Entity
from seedwork.infrastructure.database_setup import Base, Database
from seedwork.infrastructure.sqlalchemy_repository import SQLAlchemyRepository


class UserModel(Base):
    __tablename__ = "test_users_repository"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


@dataclass
class User(Entity[str]):
    name: str = ""


class UserRepository(SQLAlchemyRepository[User, UserModel]):
    def _to_domain(self, model: UserModel) -> User:
        return User(id=model.id, name=model.name)

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(id=entity.id, name=entity.name)


@pytest.fixture
def database():
    db = Database("sqlite:///:memory:")
    db.create_database()
    return db


def test_save_and_find_by_id(database):
    with database.session() as session:
        repository = UserRepository(session, UserModel)
        repository.save(User("1", "Alice"))
        session.flush()

        assert repository.find_by_id("1") == User("1", "Alice")


def test_find_by_id_returns_none_when_missing(database):
    with database.session() as session:
        repository = UserRepository(session, UserModel)

        assert repository.find_by_id("missing") is None


def test_find_all(database):
    with database.session() as session:
        repository = UserRepository(session, UserModel)
        repository.save(User("1", "Alice"))
        repository.save(User("2", "Bob"))
        session.flush()

        assert repository.find_all() == [User("1", "Alice"), User("2", "Bob")]


def test_delete(database):
    with database.session() as session:
        repository = UserRepository(session, UserModel)
        repository.save(User("1", "Alice"))
        session.flush()

        repository.delete("1")
        session.flush()

        assert repository.find_by_id("1") is None


def test_next_identity_returns_unique_string_ids(database):
    with database.session() as session:
        repository = UserRepository(session, UserModel)

        first = repository.next_identity()
        second = repository.next_identity()

        assert isinstance(first, str)
        assert first != second


def test_abstract_conversion_methods_are_required():
    with pytest.raises(TypeError):
        SQLAlchemyRepository(None, UserModel)
