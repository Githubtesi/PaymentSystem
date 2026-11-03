from typing import Any, Optional

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from .infrastructure_exceptions import ConcurrencyConflictError

from ..application.unit_of_work import IUnitOfWork


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    SQLAlchemy の Session を利用した Unit of Work の実装。

    Transaction の具体的な開始・Commit・Rollback・Session lifecycle は
    Infrastructure 層で管理し、Application 層には IUnitOfWork として公開します。
    """

    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory
        self._session: Optional[Session] = None

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        """Unit of Work を開始し、SQLAlchemy Session を生成します。"""
        self._session = self._session_factory()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Transaction を終了し、Session を必ず close します。

        - Use Case 内で例外が発生した場合: Rollback
        - 正常終了した場合: Commit
        - Commit 自体が失敗した場合: Rollback 後に例外を再送出
        """
        try:
            if self._session is None:
                return

            if exc_type is not None:
                self.rollback()
                return

            try:
                self.commit()
            except StaleDataError as exc:
                self.rollback()
                raise ConcurrencyConflictError() from exc
            except Exception:
                self.rollback()
                raise
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None

    def commit(self) -> None:
        """SQLAlchemy Session の変更を Commit します。"""
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork が開始されていません。with 構文を使用してください。"
            )

        self._session.commit()

    def rollback(self) -> None:
        """SQLAlchemy Session の変更を Rollback します。"""
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork が開始されていません。with 構文を使用してください。"
            )

        self._session.rollback()

    @property
    def session(self) -> Session:
        """Repository などが利用する SQLAlchemy Session を返します。"""
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork が開始されていません。with 構文を使用してください。"
            )

        return self._session
