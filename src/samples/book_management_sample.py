import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict

from seedwork.application import Result, IUnitOfWork, IIdentityContext, Identity
from seedwork.application.unit_of_work import T
from seedwork.domain import ValueObject, AggregateRoot, IRepository


# =========================================================
# 1. DOMAIN LAYER (ビジネスルール)
# =========================================================

@dataclass(frozen=True)
class ISBN(ValueObject):
    """ISBN（本の識別番号）の値オブジェクト"""
    value: str

    def validate(self):
        # 簡易的なチェック：10文字か13文字であること
        if len(self.value) not in [10, 13]:
            raise ValueError("ISBNは10文字または13文字である必要があります。")


class Book(AggregateRoot[uuid.UUID]):
    """
    「本」の集約ルート。
    IDには uuid.UUID を使用することを明示しています。
    """
    def __init__(self, isbn: ISBN, title: str, creator_name: str, id: uuid.UUID):
        super().__init__(id=id)
        self.isbn = isbn
        self.title = title
        self.creator_name = creator_name
        self.is_lent_out = False

    def lend(self):
        """本を貸し出す"""
        if self.is_lent_out:
            raise Exception("この本はすでに貸し出されています。")
        self.is_lent_out = True


# リポジトリのインターフェース
class IBookRepository(IRepository[Book, uuid.UUID]):
    @abstractmethod
    def find_by_isbn(self, isbn: ISBN) -> Optional[Book]: pass


# =========================================================
# 2. APPLICATION LAYER (ユースケース)
# =========================================================

@dataclass(frozen=True)
class RegisterBookCommand:
    isbn_text: str
    title: str


class RegisterBookUseCase:
    """本を新しく登録するユースケース"""

    def __init__(self, repo: IBookRepository, uow: IUnitOfWork, identity_ctx: IIdentityContext):
        self.repo = repo
        self.uow = uow
        self.identity_ctx = identity_ctx

    def execute(self, command: RegisterBookCommand) -> Result[uuid.UUID]:
        user = self.identity_ctx.current_identity
        print(f"[UseCase] {user.name} が本の登録を開始します...")

        try:
            isbn = ISBN(command.isbn_text)

            with self.uow:
                # 重複チェック
                if self.repo.find_by_isbn(isbn):
                    return Result.fail(f"このISBN({isbn.value})は既に登録されています。")

                # ドメインモデルの作成
                # ID生成はリポジトリ（またはファクトリ）の責務
                book_id = self.repo.next_identity()
                new_book = Book(isbn=isbn, title=command.title, creator_name=user.name, id=book_id)

                self.repo.save(new_book)
                self.uow.commit()

            return Result.ok(new_book.id)
        except Exception as e:
            return Result.fail(f"[{type(e).__name__}] {str(e)}")

# =========================================================
# 3. INFRASTRUCTURE LAYER (技術的な詳細 - 今回はメモリ実装)
# =========================================================

class InMemoryBookRepository(IBookRepository):
    """
    エラーの原因となっていた不足メソッドをすべて実装しました。
    """
    def __init__(self):
        self._db: Dict[uuid.UUID, Book] = {}

    def next_identity(self) -> uuid.UUID:
        return uuid.uuid4()

    def save(self, book: Book):
        self._db[book.id] = book

    def find_by_id(self, id: uuid.UUID):
        return self._db.get(id)

    def find_all(self) -> List[Book]:
        return list(self._db.values())

    def delete(self, id: uuid.UUID):
        if id in self._db:
            del self._db[id]

    def find_by_isbn(self, isbn: ISBN):
        return next((b for b in self._db.values() if b.isbn == isbn), None)

class MockUoW(IUnitOfWork):
    def __enter__(self: T) -> T:
        pass

    def rollback(self) -> None:
        pass

    def commit(self): print("[UoW] データベースへの書き込みを確定しました。")


class MockIdentityContext(IIdentityContext):
    def __init__(self, user_name: str):
        self._user = Identity(id="user-001", name=user_name, roles=["librarian"])

    @property
    def current_identity(self): return self._user


# =========================================================
# 4. EXECUTION (実行)
# =========================================================

if __name__ == "__main__":
    print("=== 図書管理システム DDD 実践サンプル (Generic ID版) ===")

    repo = InMemoryBookRepository()
    uow = MockUoW()
    id_ctx = MockIdentityContext("司書の山田さん")

    use_case = RegisterBookUseCase(repo, uow, id_ctx)

    # 1. 正常な登録
    print("\n【ケース1: 正しい本の登録】")
    cmd1 = RegisterBookCommand(isbn_text="1234567890123", title="Python DDD入門")
    res1 = use_case.execute(cmd1)
    if res1.is_success:
        print(f"✅ 登録成功! ID: {res1.value}")
    else:
        print(f"❌ 登録失敗: {res1.error}")

    # 2. バリデーションエラー（ISBNが短い）
    print("\n【ケース2: 不正なISBN】")
    cmd2 = RegisterBookCommand(isbn_text="123", title="短いISBNの本")
    res2 = use_case.execute(cmd2)
    if not res2.is_success:
        print(f"❌ 登録失敗: {res2.error}")

    # 3. ビジネスルール違反（重複登録）
    print("\n【ケース3: 重複登録のチェック】")
    res3 = use_case.execute(cmd1)
    if not res3.is_success:
        print(f"❌ 登録失敗: {res3.error}")