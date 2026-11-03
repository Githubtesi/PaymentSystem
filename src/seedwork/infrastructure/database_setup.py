from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for infrastructure models."""

    pass


class Database:
    """
    データベースの接続とセッション管理を担うクラス。

    トランザクション境界そのものは Unit of Work が管理し、
    このクラスは Engine と Session Factory の生成を担当します。
    """

    def __init__(self, db_url: str, echo: bool = False):
        self._engine = create_engine(db_url, echo=echo)
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
        )

    def create_database(self) -> None:
        """テーブルを作成します（開発・テスト用）。"""
        Base.metadata.create_all(self._engine)

    @property
    def session_factory(self) -> sessionmaker:
        return self._session_factory

    @contextmanager
    def session(self):
        """セッションをコンテキストマネージャ形式で提供します。"""
        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
