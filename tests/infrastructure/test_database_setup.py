import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from seedwork.infrastructure.database_setup import Base, Database


class UserModel(Base):
    __tablename__ = "test_users_database"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


@pytest.fixture
def database():
    db = Database("sqlite:///:memory:")
    db.create_database()
    return db


def test_database_creates_tables(database):
    with database.session() as session:
        assert session.execute(select(UserModel)).all() == []


def test_session_rolls_back_on_exception(database):
    with pytest.raises(RuntimeError):
        with database.session() as session:
            session.add(UserModel(id="1", name="Alice"))
            session.flush()
            raise RuntimeError("rollback")

    with database.session() as session:
        assert session.get(UserModel, "1") is None
