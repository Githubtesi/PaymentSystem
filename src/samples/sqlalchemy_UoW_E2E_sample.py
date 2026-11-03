import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Generic, TypeVar, Type

# SQLAlchemy 関連のインポート
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# =============================================================================
# SEEDWORK: DOMAIN LAYER (src/seedwork/domain/...)
# =============================================================================

# [Exceptions] src.seedwork.domain.exceptions
class ValueObjectValidationError(Exception):
    def __init__(self, message: str, class_name: str):
        self.message = message
        self.class_name = class_name
        super().__init__(f"Validation failed for {class_name}: {message}")

# [Value Object] src.seedwork.domain.value_object
@dataclass(frozen=True)
class ValueObject(ABC):
    def __post_init__(self):
        try:
            self.validate()
        except Exception as e:
            if not isinstance(e, ValueObjectValidationError):
                raise ValueObjectValidationError(str(e), self.__class__.__name__)
            raise e

    @abstractmethod
    def validate(self):
        pass

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ValueObject): return False
        return self.__dict__ == other.__dict__

# [Entity] src.seedwork.domain.entity
@dataclass
class Entity(ABC):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity): return False
        return self.id == other.id
    def __hash__(self) -> int:
        return hash(self.id)

class AggregateRoot(Entity):
    pass

# [Repository Interface] src.seedwork.domain.repositories
T = TypeVar('T', bound=AggregateRoot)
class Repository(Generic[T], ABC):
    @abstractmethod
    def save(self, aggregate: T) -> None: pass
    @abstractmethod
    def find_by_id(self, id: uuid.UUID) -> Optional[T]: pass

# [Unit of Work Interface] src.seedwork.domain.unit_of_work
class UnitOfWork(ABC):
    def __enter__(self) -> 'UnitOfWork':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()

    @abstractmethod
    def commit(self): pass

    @abstractmethod
    def rollback(self): pass

# =============================================================================
# SEEDWORK: INFRASTRUCTURE LAYER (src/seedwork/infrastructure/...)
# =============================================================================

# [SqlAlchemy Unit of Work] src.seedwork.infrastructure.sqlalchemy_unit_of_work
class SqlAlchemyUnitOfWork(UnitOfWork):
    """
    GitHub リポジトリの構成に基づく実装。
    セッションのライフサイクル管理とトランザクション制御を担当します。
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        self.session: Session = self.session_factory()
        # 具象リポジトリの初期化（本来は各ユースケース用UoWで定義）
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.session.close()

    def commit(self):
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.rollback()
            raise

    def rollback(self):
        self.session.rollback()

# =============================================================================
# DOMAIN LAYER (TODO アプリケーション固有)
# =============================================================================

@dataclass(frozen=True)
class TaskTitle(ValueObject):
    value: str
    def validate(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueObjectValidationError("Title cannot be empty", "TaskTitle")

class Task(AggregateRoot):
    def __init__(self, title: TaskTitle, id: Optional[uuid.UUID] = None, is_completed: bool = False):
        super().__init__(id=id or uuid.uuid4())
        self.title = title
        self.is_completed = is_completed

    def complete(self):
        self.is_completed = True

class TaskRepository(Repository[Task]):
    @abstractmethod
    def find_all(self) -> List[Task]: pass

# =============================================================================
# INFRASTRUCTURE LAYER (TODO アプリケーション固有の実装)
# =============================================================================

Base = declarative_base()

class TaskSchema(Base):
    __tablename__ = "tasks"
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)

class SqlAlchemyTaskRepository(TaskRepository):
    """
    インフラ層の具象リポジトリ。
    Seedwork の Repository インターフェースに従い、SQLAlchemy を使用して実装します。
    """
    def __init__(self, session: Session):
        self.session = session

    def save(self, task: Task) -> None:
        schema = TaskSchema(
            id=str(task.id),
            title=task.title.value,
            is_completed=task.is_completed
        )
        self.session.merge(schema)

    def find_by_id(self, id: uuid.UUID) -> Optional[Task]:
        schema = self.session.query(TaskSchema).filter_by(id=str(id)).first()
        if not schema: return None
        return Task(
            id=uuid.UUID(schema.id),
            title=TaskTitle(schema.title),
            is_completed=schema.is_completed
        )

    def find_all(self) -> List[Task]:
        schemas = self.session.query(TaskSchema).all()
        return [
            Task(id=uuid.UUID(s.id), title=TaskTitle(s.title), is_completed=s.is_completed)
            for s in schemas
        ]

class TaskUnitOfWork(SqlAlchemyUnitOfWork):
    """
    タスクドメイン専用の Unit of Work。
    リポジトリへのアクセスをユースケースに提供します。
    """
    def __enter__(self):
        super().__enter__()
        self.tasks = SqlAlchemyTaskRepository(self.session)
        return self

# =============================================================================
# APPLICATION LAYER
# =============================================================================

class TaskApplicationService:
    def __init__(self, uow: TaskUnitOfWork):
        self.uow = uow

    def create_task(self, title_text: str) -> str:
        with self.uow:
            task = Task(title=TaskTitle(title_text))
            self.uow.tasks.save(task)
            return str(task.id)

    def complete_task(self, task_id_str: str):
        with self.uow:
            task_id = uuid.UUID(task_id_str)
            task = self.uow.tasks.find_by_id(task_id)
            if task:
                task.complete()
                self.uow.tasks.save(task)

    def get_tasks(self) -> List[dict]:
        with self.uow:
            tasks = self.uow.tasks.find_all()
            return [{"id": str(t.id), "title": t.title.value, "done": t.is_completed} for t in tasks]

# =============================================================================
# E2E EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("--- GitHub Seedwork Style SQLAlchemy + UoW E2E ---")
    
    # 1. SQLAlchemy 初期化
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    
    # 2. UoW と サービスの初期化
    uow = TaskUnitOfWork(session_factory)
    app_service = TaskApplicationService(uow)
    
    try:
        # タスク作成
        print("\nAction: Creating Task...")
        task_id = app_service.create_task("Learn GitHub Seedwork Structure")
        
        # タスク完了
        print(f"Action: Completing Task {task_id[:8]}...")
        app_service.complete_task(task_id)
        
        # 検証
        tasks = app_service.get_tasks()
        print("\nResult:")
        for t in tasks:
            status = "✅" if t['done'] else "❌"
            print(f" {status} {t['title']}")
            
        assert len(tasks) == 1
        assert tasks[0]['done'] is True
        print("\n--- Success! ---")
        
    except Exception as e:
        print(f"Error: {e}")
