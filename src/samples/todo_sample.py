"""
【初心者向け解説：タスク管理システムの仕組み】
このプログラムは、やるべきこと（タスク）を作成し、それを「完了」させるまでの流れを表現しています。

1. [値のチェック]：タスク名が短すぎないか、期限が過去じゃないか確認します（ValueObject）
2. [タスクを作る]：「未完了」状態でタスクを誕生させます（Entity/AggregateRoot）
3. [状態を変える]：タスクを「完了」の状態に変化させます。この時「二重完了」を防ぎます（Business Logic）
4. [出来事を記録]：「タスクが終わった！」という事実をメモします（DomainEvent）
5. [ご褒美を出す]：完了メモを見て、お祝いメッセージを表示します（EventPublisher/Subscriber）
"""

from dataclasses import dataclass
from datetime import datetime, date
from seedwork.domain import (
    ValueObject, 
    AggregateRoot, 
    IRepository, 
    DomainEvent, 
    DomainEventSubscriber, 
    publisher,
    ValueObjectValidationError
)

# ---------------------------------------------------------
# 1. 値のルールを決める（Value Objects）
# 想定ファイル: src.todo.domain.models.task.value_objects
# ---------------------------------------------------------

@dataclass(frozen=True)
class TaskTitle(ValueObject):
    """タスクのタイトル。3文字以上、50文字以内というルールを守らせます。"""
    value: str

    def validate(self):
        if len(self.value) < 3:
            raise ValueObjectValidationError("タイトルが短すぎます（3文字以上必要）", "TaskTitle")
        if len(self.value) > 50:
            raise ValueObjectValidationError("タイトルが長すぎます（50文字以内）", "TaskTitle")

@dataclass(frozen=True)
class DueDate(ValueObject):
    """タスクの期限。過去の日付は設定できないルールにします。"""
    value: date

    def validate(self):
        if self.value < date.today():
            raise ValueObjectValidationError("過去の日付は期限に設定できません", "DueDate")

# ---------------------------------------------------------
# 2. 起こった出来事を定義する（Domain Event）
# 想定ファイル: src.todo.domain.models.task.task_events
# ---------------------------------------------------------

@dataclass(frozen=True)
class TaskCompleted(DomainEvent):
    """「タスクが完了した」という事実を表します。"""
    title: str

# ---------------------------------------------------------
# 3. タスクという「物」を定義する（Aggregate Root）
# 想定ファイル: src.todo.domain.models.task.task
# ---------------------------------------------------------

@dataclass
class Task(AggregateRoot[str]):
    """
    タスク本人です。ID、タイトル、期限、そして「完了したか」の情報を持ちます。
    """
    title: TaskTitle
    due_date: DueDate
    is_completed: bool = False

    @classmethod
    def create(cls, task_id: str, title: TaskTitle, due_date: DueDate) -> "Task":
        """新しいタスクを「未完了」状態で作成します。"""
        return cls(id=task_id, title=title, due_date=due_date, is_completed=False)

    def complete(self):
        """
        タスクを完了状態にします。
        「すでに完了していたらエラー」というビジネスルールをここで守ります。
        """
        if self.is_completed:
            # 業務ルールに反する場合もエラーを投げます
            raise Exception(f"タスク『{self.title.value}』はすでに完了しています。")

        self.is_completed = True
        
        # 「完了した！」というイベントを自分の中に記録します
        self.record_event(TaskCompleted(
            aggregate_id=self.id,
            title=self.title.value
        ))
        print(f"[Domain] タスク『{self.title.value}』を完了状態にしました。")

# ---------------------------------------------------------
# 4. 保存の窓口（Repository Interface）
# 想定ファイル: src.todo.domain.models.task.i_task_repository
# ---------------------------------------------------------

class ITaskRepository(IRepository[Task]):
    pass

# ---------------------------------------------------------
# 5. 実際に保存する仕組み（Infrastructure Implementation）
# 想定ファイル: src.todo.infrastructure.repositories.task_repository_impl
# ---------------------------------------------------------

class InMemoryTaskRepositoryImpl(ITaskRepository):
    def __init__(self):
        self._tasks = {}

    def next_identity(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8] # 短いIDにします

    def save(self, task: Task) -> None:
        self._tasks[task.id] = task
        print(f"[Infrastructure] タスク {task.id} を保存しました。")

    def find_by_id(self, task_id: str):
        return self._tasks.get(task_id)

    def delete(self, task_id: str):
        if task_id in self._tasks: del self._tasks[task_id]

    def find_all(self):
        return list(self._tasks.values())

# ---------------------------------------------------------
# 6. イベントに反応する人（Subscriber）
# 想定ファイル: src.todo.application.handlers.congratulation_handler
# ---------------------------------------------------------

class CongratulationHandler(DomainEventSubscriber):
    """タスク完了イベントを見て、お祝いの言葉をかける担当です。"""
    @property
    def subscribed_to_type(self):
        return TaskCompleted

    def handle(self, event: TaskCompleted):
        print(f"✨ [お祝いサービス] おめでとうございます！『{event.title}』を達成しましたね！ ✨")

# ---------------------------------------------------------
# 7. 手順をまとめる（Application Service）
# 想定ファイル: src.todo.application.task.task_app_service
# ---------------------------------------------------------

class TaskAppService:
    def __init__(self, repository: ITaskRepository):
        self._repository = repository

    def add_new_task(self, title_str: str, due_date_val: date):
        """新しいタスクを追加する手順"""
        print(f"\n>> タスク追加依頼: {title_str}")
        try:
            tid = self._repository.next_identity()
            title = TaskTitle(title_str)   # バリデーション
            due = DueDate(due_date_val)    # バリデーション
            
            task = Task.create(tid, title, due)
            self._repository.save(task)
            
            print(f"<< タスク作成完了 (ID: {tid})")
            return tid
        except ValueObjectValidationError as e:
            print(f"【入力エラー】{e.message}")
            return None

    def mark_as_complete(self, task_id: str):
        """タスクを完了させる手順"""
        print(f"\n>> タスク完了操作: ID {task_id}")
        
        # 1. リポジトリから今の状態のタスクを取り出す
        task = self._repository.find_by_id(task_id)
        if not task:
            print(f"【エラー】ID {task_id} のタスクが見つかりません。")
            return

        try:
            # 2. タスク本人に「完了して」と頼む（ここでビジネスルールがチェックされる）
            task.complete()

            # 3. 変化した状態を保存する
            self._repository.save(task)

            # 4. 溜まったイベントを発行する
            events = task.pull_events()
            publisher.publish_all(events)
            
        except Exception as e:
            print(f"【操作エラー】{e}")

# ---------------------------------------------------------
# 8. 動かしてみる（Main / Entry Point）
# 想定ファイル: main.py
# ---------------------------------------------------------

if __name__ == "__main__":
    # 準備
    publisher.subscribe(CongratulationHandler())
    repo = InMemoryTaskRepositoryImpl()
    service = TaskAppService(repo)

    # --- 1. 正常なタスク追加 ---
    tid = service.add_new_task("DDDの勉強をする", date(2026, 12, 31))

    # --- 2. タスクを完了させる (お祝いが出るはず) ---
    if tid:
        service.mark_as_complete(tid)

    # --- 3. 同じタスクをもう一度完了させてみる (エラーになるはず) ---
    if tid:
        service.mark_as_complete(tid)

    # --- 4. 異常なタスク追加 (期限が過去) ---
    service.add_new_task("過去に戻る", date(2020, 1, 1))

    # --- 5. 異常なタスク追加 (タイトルが短い) ---
    service.add_new_task("あ", date(2026, 5, 5))
