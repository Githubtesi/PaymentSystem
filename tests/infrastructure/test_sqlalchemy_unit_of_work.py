import pytest
from sqlalchemy import String

from sqlalchemy.orm import Mapped, mapped_column

from seedwork.infrastructure.database_setup import Base, Database
from seedwork.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork


class UserModel(Base):
    __tablename__ = "test_users_uow"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class OrderModel(Base):
    __tablename__ = "test_orders_uow"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(String(100))


@pytest.fixture
def database():
    db = Database("sqlite:///:memory:")
    db.create_database()
    return db


def test_successful_context_commits(database):
    uow = SQLAlchemyUnitOfWork(database.session_factory)

    with uow:
        uow.session.add(UserModel(id="1", name="Alice"))

    with database.session() as session:
        assert session.get(UserModel, "1").name == "Alice"


def test_transaction_boundary_commits_multiple_changes(database):
    uow = SQLAlchemyUnitOfWork(database.session_factory)

    with uow:
        uow.session.add(UserModel(id="1", name="Alice"))
        uow.session.add(OrderModel(id="1", description="Order 1"))

    with database.session() as session:
        assert session.get(UserModel, "1") is not None
        assert session.get(OrderModel, "1") is not None


def test_transaction_boundary_rolls_back_all_changes(database):
    uow = SQLAlchemyUnitOfWork(database.session_factory)

    with pytest.raises(RuntimeError):
        with uow:
            uow.session.add(UserModel(id="1", name="Alice"))
            uow.session.add(OrderModel(id="1", description="Order 1"))
            raise RuntimeError("rollback all")

    with database.session() as session:
        assert session.get(UserModel, "1") is None
        assert session.get(OrderModel, "1") is None


def test_exception_context_rolls_back(database):
    uow = SQLAlchemyUnitOfWork(database.session_factory)

    with pytest.raises(RuntimeError):
        with uow:
            uow.session.add(UserModel(id="1", name="Alice"))
            raise RuntimeError("rollback")

    with database.session() as session:
        assert session.get(UserModel, "1") is None


def test_commit_failure_rolls_back_and_closes_session():
    class FailingSession:
        def __init__(self):
            self.rollback_called = False
            self.close_called = False

        def commit(self):
            raise RuntimeError("commit failed")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            self.close_called = True

    factory = lambda: FailingSession()
    uow = SQLAlchemyUnitOfWork(factory)

    with pytest.raises(RuntimeError, match="commit failed"):
        with uow:
            pass

    assert uow._session is None


def test_operations_before_enter_raise_runtime_error(database):
    uow = SQLAlchemyUnitOfWork(database.session_factory)

    with pytest.raises(RuntimeError):
        uow.commit()

    with pytest.raises(RuntimeError):
        uow.rollback()

    with pytest.raises(RuntimeError):
        _ = uow.session
