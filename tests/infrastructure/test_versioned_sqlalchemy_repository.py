from dataclasses import dataclass

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from seedwork.domain.versioned_entity import VersionedEntity
from seedwork.infrastructure.database_setup import Base, Database
from seedwork.infrastructure.infrastructure_exceptions import ConcurrencyConflictError
from seedwork.infrastructure.sqlalchemy_repository import VersionedSQLAlchemyRepository


class OrderModel(Base):
    __tablename__ = "test_orders_versioned"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    total: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}


@dataclass(eq=False)
class Order(VersionedEntity[str]):
    total: int = 0


class OrderRepository(VersionedSQLAlchemyRepository[Order, OrderModel]):
    def _to_domain(self, model: OrderModel) -> Order:
        return Order(id=model.id, total=model.total, version=model.version)

    def _to_model(self, entity: Order) -> OrderModel:
        return OrderModel(id=entity.id, total=entity.total, version=entity.version)


@pytest.fixture
def database(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'versioned.db'}")
    db.create_database()
    return db


def test_save_initializes_version_and_updates_domain_version(database):
    with database.session() as session:
        repository = OrderRepository(session, OrderModel)
        order = Order("1", 100)

        repository.save(order)

        assert order.version == 1

        order.total = 120
        repository.save(order)

        assert order.version == 2


def test_stale_update_raises_concurrency_conflict(database):
    with database.session() as session:
        repository = OrderRepository(session, OrderModel)
        repository.save(Order("1", 100))
        session.commit()

    with database.session() as session1, database.session() as session2:
        repository1 = OrderRepository(session1, OrderModel)
        repository2 = OrderRepository(session2, OrderModel)
        order1 = repository1.find_by_id("1")
        order2 = repository2.find_by_id("1")

        order1.total = 110
        repository1.save(order1)
        session1.commit()

        order2.total = 120
        with pytest.raises(ConcurrencyConflictError):
            repository2.save(order2)


def test_versioned_repository_requires_mapper_version_column(database):
    class InvalidModel(Base):
        __tablename__ = "test_invalid_versioned"
        id: Mapped[str] = mapped_column(String(36), primary_key=True)

    class InvalidRepository(VersionedSQLAlchemyRepository[Order, InvalidModel]):
        def _to_domain(self, model: InvalidModel) -> Order:
            return Order(id=model.id, total=0)

        def _to_model(self, entity: Order) -> InvalidModel:
            return InvalidModel(id=entity.id)

    with database.session() as session:
        with pytest.raises(ValueError):
            InvalidRepository(session, InvalidModel)
