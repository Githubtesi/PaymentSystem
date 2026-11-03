import sqlite3
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Generic, TypeVar

# =============================================================================
# SEEDWORK (ドメイン共通基盤)
# ドメイン駆動設計における「種（Seed）」となる基底クラス群です。
# 全てのドメインモデルはこの基盤を継承することで、DDDのパターンを強制します。
# =============================================================================

# 想定ファイル: src.seedwork.domain.exceptions
class ValueObjectValidationError(Exception):
    """
    値オブジェクトのバリデーション失敗時にスローされる例外。
    ドメインの整合性が損なわれたことを明示します。
    """
    def __init__(self, message: str, class_name: str):
        self.message = message
        self.class_name = class_name
        super().__init__(f"Validation failed for {class_name}: {message}")

# 想定ファイル: src.seedwork.domain.value_object
@dataclass(frozen=True)
class ValueObject(ABC):
    """
    値オブジェクト (Value Object) の基底クラス。
    - 不変 (Immutable): 一度作成されたら値を変えられません。
    - 値による比較: 識別子を持たず、属性値が同じであれば同じものとみなします。
    - 自己バリデーション: 生成時に __post_init__ で自身の正当性をチェックします。
    """
    def __post_init__(self):
        try:
            self.validate()
        except Exception as e:
            # 予期せぬエラーもバリデーションエラーとしてラップし、ドメイン境界を守ります
            if not isinstance(e, ValueObjectValidationError):
                raise ValueObjectValidationError(str(e), self.__class__.__name__)
            raise e

    @abstractmethod
    def validate(self):
        """ビジネスルールに基づくバリデーションを実装します。"""
        pass

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ValueObject):
            return False
        return self.__dict__ == other.__dict__

# 想定ファイル: src.seedwork.domain.entity
@dataclass
class Entity(ABC):
    """
    エンティティ (Entity) の基底クラス。
    - 同一性 (Identity): 属性が変わっても、一意識別子 (id) によって「同じもの」として扱われます。
    - 可変性: ライフサイクルを通じて状態が変化することが許容されます。
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

# 想定ファイル: src.seedwork.domain.aggregate_root
class AggregateRoot(Entity):
    """
    集約ルート (Aggregate Root) の基底クラス。
    - 整合性の境界: 関連するオブジェクト群を一つの単位（集約）としてまとめ、その入り口となります。
    - 外部からの操作は必ずこの集約ルートを介して行われます。
    """
    pass

# 想定ファイル: src.seedwork.domain.repositories
T = TypeVar('T', bound=AggregateRoot)

class Repository(Generic[T], ABC):
    """
    リポジトリ (Repository) の抽象基底クラス。
    - 集約の永続化と再構築を抽象化します。
    - ドメイン層にインターフェースを置くことで、具体的なDB実装からドメインを隔離します。
    """
    @abstractmethod
    def save(self, aggregate: T) -> None:
        """集約の状態を保存（または更新）します。"""
        pass

    @abstractmethod
    def find_by_id(self, id: uuid.UUID) -> Optional[T]:
        """IDを指定して集約を再構築します。"""
        pass

# =============================================================================
# DOMAIN LAYER (ドメイン層)
# ビジネスロジックの本質を記述するレイヤーです。
# 技術的な詳細（DB、UI等）には依存せず、純粋なビジネスルールのみを持ちます。
# =============================================================================

# 想定ファイル: src.todo.domain.models.task.value_objects
@dataclass(frozen=True)
class TaskTitle(ValueObject):
    """タスクのタイトルを表す値オブジェクト。"""
    value: str

    def validate(self):
        # タイトルは空であってはならず、長さにも制限があるというビジネスルール
        if not self.value or len(self.value.strip()) == 0:
            raise ValueObjectValidationError("Title cannot be empty", self.__class__.__name__)
        if len(self.value) > 100:
            raise ValueObjectValidationError("Title is too long", self.__class__.__name__)

@dataclass(frozen=True)
class TaskStatus(ValueObject):
    """タスクの完了状態を表す値オブジェクト。"""
    is_completed: bool = False

    def validate(self):
        if not isinstance(self.is_completed, bool):
            raise ValueObjectValidationError("Status must be boolean", self.__class__.__name__)

# 想定ファイル: src.todo.domain.models.task.entities
class Task(AggregateRoot):
    """
    タスク (Task) 集約。
    このクラスがタスクに関する全てのビジネスルールをコントロールします。
    """
    def __init__(
        self, 
        title: TaskTitle, 
        id: Optional[uuid.UUID] = None,
        status: Optional[TaskStatus] = None,
        created_at: Optional[datetime] = None
    ):
        super().__init__(id=id or uuid.uuid4())
        self.title = title
        self.status = status or TaskStatus()
        self.created_at = created_at or datetime.now()

    def complete(self):
        """タスクを完了させる。外部から直接 status を書き換えるのではなく、このメソッドを呼びます。"""
        self.status = TaskStatus(is_completed=True)

    def change_title(self, new_title: TaskTitle):
        """タイトルを変更するビジネスアクション。"""
        self.title = new_title

# 想定ファイル: src.todo.domain.repositories.task_repository
class TaskRepository(Repository[Task]):
    """ドメイン層で定義されるタスク専用のリポジトリインターフェース。"""
    @abstractmethod
    def find_all(self) -> List[Task]:
        """全件取得の要件をドメイン側で定義します。"""
        pass

# =============================================================================
# INFRASTRUCTURE LAYER (インフラストラクチャ層)
# 技術的な詳細（SQLite, 外部API, ファイルシステム等）を実装するレイヤーです。
# ドメイン層で定義されたインターフェース（Repository）を具象化します。
# =============================================================================

# 想定ファイル: src.todo.infrastructure.repositories.sqlite_task_repository
class SQLiteTaskRepository(TaskRepository):
    """SQLiteを使用したリポジトリの具象実装。"""
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self._create_table()

    def _create_table(self):
        """データベーステーブルの初期化。"""
        query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            is_completed INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def save(self, task: Task) -> None:
        """集約の状態をDBに反映します（マッピング処理）。"""
        query = """
        INSERT OR REPLACE INTO tasks (id, title, is_completed, created_at)
        VALUES (?, ?, ?, ?)
        """
        self.conn.execute(query, (
            str(task.id),
            task.title.value,
            1 if task.status.is_completed else 0,
            task.created_at.isoformat()
        ))
        self.conn.commit()

    def find_by_id(self, id: uuid.UUID) -> Optional[Task]:
        """DBからデータを取得し、ドメインモデル（Task）を再構築します。"""
        cursor = self.conn.execute(
            "SELECT id, title, is_completed, created_at FROM tasks WHERE id = ?", 
            (str(id),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return Task(
            id=uuid.UUID(row[0]),
            title=TaskTitle(row[1]),
            status=TaskStatus(is_completed=bool(row[2])),
            created_at=datetime.fromisoformat(row[3])
        )

    def find_all(self) -> List[Task]:
        """全レコードを取得し、ドメインモデルのリストとして返します。"""
        cursor = self.conn.execute("SELECT id, title, is_completed, created_at FROM tasks")
        tasks = []
        for row in cursor.fetchall():
            tasks.append(Task(
                id=uuid.UUID(row[0]),
                title=TaskTitle(row[1]),
                status=TaskStatus(is_completed=bool(row[2])),
                created_at=datetime.fromisoformat(row[3])
            ))
        return tasks

# =============================================================================
# APPLICATION LAYER (アプリケーション層 / ユースケース)
# ユースケースを実現するためにドメインモデルを調整（Orchestration）するレイヤーです。
# ビジネスルール自体は持ちませんが、リポジトリから集約を取得し、操作を命じ、保存を呼び出します。
# =============================================================================

# 想定ファイル: src.todo.application.use_cases.task_use_cases
class TaskApplicationService:
    """タスクに関するユースケースを処理するアプリケーションサービス。"""
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def create_task(self, title_text: str) -> str:
        """「タスクを新規作成する」というユースケース。"""
        # 値オブジェクトの生成（この時点で不正なデータはバリデーションで弾かれる）
        title = TaskTitle(title_text)
        # ドメインモデルの生成
        task = Task(title=title)
        # リポジトリによる永続化
        self.repository.save(task)
        return str(task.id)

    def complete_task(self, task_id_str: str):
        """「タスクを完了させる」というユースケース。"""
        task_id = uuid.UUID(task_id_str)
        # リポジトリを介して集約を取得
        task = self.repository.find_by_id(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id_str} not found")
        
        # ドメインモデルにビジネスロジックの実行を依頼
        task.complete()
        # 変更された状態を永続化
        self.repository.save(task)

    def list_tasks(self) -> List[dict]:
        """「タスク一覧を表示する」というユースケース（DTO的にデータを整形して返します）。"""
        tasks = self.repository.find_all()
        return [
            {
                "id": str(t.id), 
                "title": t.title.value, 
                "completed": t.status.is_completed,
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for t in tasks
        ]

# =============================================================================
# E2E EXECUTION (エンドツーエンドテスト実行)
# 実際のユーザー操作やシステム統合を模したテストスクリプトです。
# =============================================================================

if __name__ == "__main__":
    print("--- SQLite DDD E2E Scenario Starting ---")
    
    # 1. 依存性の注入 (Dependency Injection)
    # 本番環境では PostgreSQL や MySQL に差し替えることが可能ですが、
    # ドメイン層やアプリケーション層のコードを変更する必要はありません。
    connection = sqlite3.connect(":memory:")
    repository = SQLiteTaskRepository(connection)
    
    # 2. サービスの組み立て
    app_service = TaskApplicationService(repository)
    
    try:
        # シナリオ A: 正常なワークフロー
        print("\n[Scenario A] Creating a valid task...")
        task_id = app_service.create_task("Finish DDD Sample")
        print(f"-> Success: Task created with ID {task_id[:8]}...")

        # シナリオ B: ドメインルールの検証
        print("\n[Scenario B] Attempting to create an invalid task (empty title)...")
        try:
            app_service.create_task("   ") # スペースのみの不正な入力
        except ValueObjectValidationError as e:
            # ドメイン層のガードレールが正しく機能していることを確認
            print(f"-> Caught expected validation error: {e.message}")

        # シナリオ C: 状態遷移の実行
        print(f"\n[Scenario C] Completing task {task_id[:8]}...")
        app_service.complete_task(task_id)
        print("-> Success: Task marked as completed.")

        # シナリオ D: 最終的な状態の確認
        print("\n[Scenario D] Fetching all tasks and verifying results...")
        tasks = app_service.list_tasks()
        for t in tasks:
            status = "DONE" if t['completed'] else "TODO"
            print(f" [{status}] {t['title']} (Created: {t['created_at']})")

        # 結果の整合性チェック
        assert len(tasks) == 1
        assert tasks[0]['completed'] is True
        print("\n--- All E2E Scenarios Completed Successfully ---")

    finally:
        # リソースのクリーンアップ
        connection.close()
