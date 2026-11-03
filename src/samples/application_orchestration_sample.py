"""
【アプリケーション層フォーカス・サンプル：タスク作成ユースケース】
このサンプルでは、ドメイン層のロジックは最小限に抑え、
アプリケーション層がどのように「認証」「トランザクション」「結果返却」を制御するかを示します。

■ 使用しているアプリケーション基盤:
1. Command: 入力データの定義
2. IUseCase: 処理の実行単位
3. IUnitOfWork: トランザクション管理
4. IIdentityContext: 「誰が」実行しているかの取得
5. Result: 成功・失敗の型安全な返却
"""

from dataclasses import dataclass
from datetime import datetime

# Seedworkからのインポート（パスはプロジェクト構成に合わせて調整）
from seedwork.domain import AggregateRoot, IRepository
from seedwork.application import (
    Command, IUseCase, IUnitOfWork, Result, 
    Identity, IIdentityContext, ValidationError, AuthorizationError
)

# ---------------------------------------------------------
# 1. Minimal Domain (ドメイン層は軽く)
# ---------------------------------------------------------

@dataclass
class Task(AggregateRoot[str]):
    title: str
    owner_id: str
    created_at: datetime

class ITaskRepository(IRepository[Task]):
    """タスク保存用の窓口"""
    pass

# ---------------------------------------------------------
# 2. Application Layer - Command (入力)
# ---------------------------------------------------------

@dataclass(frozen=True)
class CreateTaskCommand(Command):
    """タスク作成に必要な情報をまとめたDTO"""
    title: str

# ---------------------------------------------------------
# 3. Application Layer - Use Case (実行)
# ---------------------------------------------------------

class CreateTaskUseCase(IUseCase[CreateTaskCommand, str]):
    """
    タスク作成のユースケース。
    手順：認証チェック -> バリデーション -> ドメイン操作 -> 保存 -> 結果返却
    """
    def __init__(
        self, 
        repository: ITaskRepository, 
        uow: IUnitOfWork, 
        identity_context: IIdentityContext
    ):
        self._repository = repository
        self._uow = uow
        self._identity_context = identity_context

    def execute(self, command: CreateTaskCommand) -> Result[str]:
        # A. 認証・権限の確認 (Identity)
        identity = self._identity_context.current_identity
        if not identity.is_in_role("user"):
            return Result.fail("ログインが必要です")

        # B. 入力バリデーション (ValidationErrorのシミュレーション)
        if len(command.title) < 3:
            return Result.fail("タイトルが短すぎます")

        try:
            # C. トランザクション開始 (Unit of Work)
            with self._uow:
                # D. ドメインオブジェクトの生成 (Domain)
                task_id = self._repository.next_identity()
                new_task = Task(
                    id=task_id, 
                    title=command.title, 
                    owner_id=identity.id,
                    created_at=datetime.now()
                )
                
                # E. 保存 (Repository)
                self._repository.save(new_task)
                
                # withブロックを抜ける際に uow.commit() が自動で呼ばれます
            
            # F. 成功結果の返却 (Result)
            print(f"[UseCase] タスク '{command.title}' (ID: {task_id}) を作成しました。")
            return Result.ok(task_id)

        except Exception as e:
            # ロールバックは uow.__exit__ で自動で行われます
            return Result.fail(f"システムエラーが発生しました: {str(e)}")

# ---------------------------------------------------------
# 4. Infrastructure Layer - Mocks (動作確認用の仮実装)
# ---------------------------------------------------------

class MockTaskRepository(ITaskRepository):
    def next_identity(self) -> str: return "task-123"
    def save(self, entity: Task): print(f"[Repo] DBに保存完了: {entity.id}")
    def find_by_id(self, id: str): return None
    def delete(self, id: str): pass
    def find_all(self): return []

class MockUnitOfWork(IUnitOfWork):
    def __enter__(self): print("[UoW] トランザクション開始"); return self
    def commit(self): print("[UoW] コミット（確定）しました")
    def rollback(self): print("[UoW] ロールバック（破棄）しました")


class MockIdentityContext(IIdentityContext):
    def __init__(self, user_id: str):
        # ロール名を "user" に修正して判定をパスするようにします
        roles = ["user"] if user_id else []
        self._user = Identity(id=user_id, name="test_user", roles=roles)

    @property
    def current_identity(self) -> Identity:
        return self._user

# ---------------------------------------------------------
# 5. Execution (メイン処理)
# ---------------------------------------------------------

if __name__ == "__main__":
    # 依存関係の準備 (DI)
    repo = MockTaskRepository()
    uow = MockUnitOfWork()
    
    # --- パターン1: 成功ケース (ログイン済みユーザー) ---
    ctx_ok = MockIdentityContext(user_id="user-001")
    usecase = CreateTaskUseCase(repo, uow, ctx_ok)
    
    cmd = CreateTaskCommand(title="DDDのシードワークを完成させる")
    result = usecase.execute(cmd)
    
    if result.is_success:
        print(f"結果: 成功 (生成ID: {result.value})")

    # --- パターン2: 失敗ケース (未ログインユーザー) ---
    print("\n--- 未ログインの場合 ---")
    ctx_guest = MockIdentityContext(user_id="")
    usecase_guest = CreateTaskUseCase(repo, uow, ctx_guest)
    
    result_fail = usecase_guest.execute(cmd)
    if not result_fail.is_success:
        print(f"結果: 失敗 (理由: {result_fail.error})")
