import sqlite3
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Generic, TypeVar, Dict, Type

from seedwork.application import IUnitOfWork, IIdentityContext, Result, Identity
from seedwork.domain import ValueObject, AggregateRoot, IRepository


# =============================================================================
# 1. DOMAIN LAYER (ビジネスルール)
# =============================================================================

@dataclass(frozen=True)
class MemoContent(ValueObject):
    """メモの内容を表す値オブジェクト。"""
    value: str

    def validate(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("メモの内容が空です。")
        if len(self.value) > 200:
            raise ValueError("メモが長すぎます（200文字以内）。")


class Memo(AggregateRoot[uuid.UUID]):
    """メモの集約ルート。"""

    def __init__(self, content: MemoContent, author_name: str, id: uuid.UUID, created_at: Optional[datetime] = None):
        super().__init__(id=id)
        self.content = content
        self.author_name = author_name
        self.created_at = created_at or datetime.now()


class IMemoRepository(IRepository[Memo]):
    """メモ専用のリポジトリ（追加の検索条件などがあればここに定義）"""
    pass


# =============================================================================
# 2. APPLICATION LAYER (ユースケース)
# =============================================================================

@dataclass(frozen=True)
class CreateMemoCommand:
    text: str


class CreateMemoUseCase:
    """メモを作成して保存するユースケース。"""

    def __init__(self, repo: IMemoRepository, uow: IUnitOfWork, identity_ctx: IIdentityContext):
        self.repo = repo
        self.uow = uow
        self.identity_ctx = identity_ctx

    def execute(self, command: CreateMemoCommand) -> Result[uuid.UUID]:
        user = self.identity_ctx.current_identity

        try:
            # 1. バリデーション（値オブジェクトの作成）
            content = MemoContent(command.text)

            # 2. トランザクション開始
            with self.uow:
                # 3. エンティティの作成
                memo_id = self.repo.next_identity()
                new_memo = Memo(content=content, author_name=user.name, id=memo_id)

                # 4. 保存
                self.repo.save(new_memo)
                self.uow.commit()  # ここで確定

            return Result.ok(new_memo.id)
        except Exception as e:
            return Result.fail(str(e))


# =============================================================================
# 3. INFRASTRUCTURE LAYER (SQLite による実装)
# =============================================================================

class SQLiteMemoRepository(IMemoRepository):
    """SQLite を使ったリポジトリの具象実装。"""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self._setup_db()

    def _setup_db(self):
        """テーブル作成。"""
        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS memos
                          (
                              id
                              TEXT
                              PRIMARY
                              KEY,
                              content
                              TEXT,
                              author_name
                              TEXT,
                              created_at
                              TEXT
                          )
                          """)

    def next_identity(self) -> uuid.UUID:
        return uuid.uuid4()

    def save(self, memo: Memo):
        """ドメインモデルをDBの形式に変換して保存。"""
        self.conn.execute(
            "INSERT OR REPLACE INTO memos (id, content, author_name, created_at) VALUES (?, ?, ?, ?)",
            (str(memo.id), memo.content.value, memo.author_name, memo.created_at.isoformat())
        )

    def find_by_id(self, id: uuid.UUID) -> Optional[Memo]:
        cursor = self.conn.execute("SELECT * FROM memos WHERE id = ?", (str(id),))
        row = cursor.fetchone()
        if not row: return None
        return Memo(
            id=uuid.UUID(row[0]),
            content=MemoContent(row[1]),
            author_name=row[2],
            created_at=datetime.fromisoformat(row[3])
        )

    def find_all(self) -> List[Memo]:
        cursor = self.conn.execute("SELECT * FROM memos ORDER BY created_at DESC")
        return [
            Memo(
                id=uuid.UUID(row[0]),
                content=MemoContent(row[1]),
                author_name=row[2],
                created_at=datetime.fromisoformat(row[3])
            ) for row in cursor.fetchall()
        ]

    def delete(self, id: uuid.UUID):
        self.conn.execute("DELETE FROM memos WHERE id = ?", (str(id),))



class SqlAlchemyUnitOfWork(IUnitOfWork):
    """
    SQLAlchemyを使用した具体的なUoW実装。
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None

    def __enter__(self):
        self.session = self.session_factory()
        # ここでリポジトリの初期化などを行う
        # self.users = UserRepository(self.session)
        return super().__enter__()

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            if self.session:
                self.session.close()

class MemoryUnitOfWork(IUnitOfWork):
    """
    テスト用のインメモリUoW実装。
    """
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True



class MockIdentityContext(IIdentityContext):
    def __init__(self, name: str):
        self._user = Identity(id="user-001", name=name)

    @property
    def current_identity(self) -> Identity:
        return self._user


def save_user_service(uow: IUnitOfWork, user_data: dict):
    """
    サービス層での利用例。具体的な実装(SQLAlchemy等)に依存せず、
    インターフェース(IUnitOfWork)に依存することで、テストが容易になります。
    """
    with uow:
        # ここでデータの操作を行う
        # uow.users.add(User(**user_data))
        print(f"Processing data: {user_data}")

        # 例外が発生すれば自動で rollback() が呼ばれ、
        # 無事に終了すれば自動で commit() が呼ばれます。
        pass

# =============================================================================
# 4. EXECUTION (実行シナリオ)
# =============================================================================
if __name__ == "__main__":
    # テスト用UoWでの実行
    mock_uow = MemoryUnitOfWork()
    save_user_service(mock_uow, {"name": "Alice"})
    print(f"Committed: {mock_uow.committed}")