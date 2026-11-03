from abc import abstractmethod
from typing import Any, Generic, List, Optional, Type, TypeVar
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from ..domain.entity import Entity
from ..domain.versioned_entity import VersionedEntity
from ..domain.repository import IRepository
from .infrastructure_exceptions import ConcurrencyConflictError

T_Entity = TypeVar("T_Entity", bound=Entity)
T_VersionedEntity = TypeVar("T_VersionedEntity", bound=VersionedEntity)
T_Model = TypeVar("T_Model")

class SQLAlchemyRepository(IRepository[T_Entity, Any], Generic[T_Entity, T_Model]):
    """SQLAlchemyを使用した通常のRepository基底クラス。"""
    def __init__(self, session: Session, model_type: Type[T_Model]):
        self._session = session
        self._model_type = model_type

    def save(self, entity: T_Entity) -> None:
        model = self._to_model(entity)
        self._session.merge(model)

    def find_by_id(self, entity_id: Any) -> Optional[T_Entity]:
        model = self._session.get(self._model_type, entity_id)
        return self._to_domain(model) if model is not None else None

    def delete(self, entity_id: Any) -> None:
        model = self._session.get(self._model_type, entity_id)
        if model is not None:
            self._session.delete(model)

    def find_all(self) -> List[T_Entity]:
        statement = select(self._model_type)
        models = self._session.scalars(statement).all()
        return [self._to_domain(model) for model in models]

    def next_identity(self) -> str:
        return str(uuid.uuid4())

    @abstractmethod
    def _to_domain(self, model: T_Model) -> T_Entity:
        raise NotImplementedError

    @abstractmethod
    def _to_model(self, entity: T_Entity) -> T_Model:
        raise NotImplementedError


class VersionedSQLAlchemyRepository(SQLAlchemyRepository[T_VersionedEntity, T_Model], Generic[T_VersionedEntity, T_Model]):
    """SQLAlchemyのversion_id_colを利用する楽観的ロック対応Repository。

    DB Modelはversionカラムを持ち、SQLAlchemy mapperで
    __mapper_args__ = {"version_id_col": version} を設定することを前提とする。
    保存時にflushして競合を即時検出し、成功した新しいVersionをDomain Entityへ反映する。
    """
    def __init__(self, session: Session, model_type: Type[T_Model]):
        super().__init__(session, model_type)
        mapper = model_type.__mapper__
        version_column = mapper.version_id_col
        if version_column is None or getattr(version_column, "key", None) != "version":
            raise ValueError("VersionedSQLAlchemyRepository requires a model with a 'version' column configured as SQLAlchemy version_id_col")

    def save(self, entity: T_VersionedEntity) -> None:
        model = self._to_model(entity)
        try:
            merged = self._session.merge(model)
            self._session.flush()
        except StaleDataError as exc:
            raise ConcurrencyConflictError() from exc
        entity.version = int(getattr(merged, "version"))
