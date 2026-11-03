"""
【大規模向け：バス・オーケストレーション・サンプル】
このサンプルでは、Command Bus と Query Bus を使って、
アプリケーションの各機能（ユースケース）を完全に分離・独立させる方法を示します。

■ メリット:
1. 低結合: コントローラーは Bus しか知りません。
2. 拡張性: 新しい機能を追加する際、既存のコードを触らずに「ハンドラ」を登録するだけ。
3. テスト容易性: 各ハンドラが独立しているため、ユニットテストが書きやすい。
"""

from dataclasses import dataclass, field
from typing import List, Any
from datetime import datetime

# Seedworkからのインポート
from seedwork.domain import AggregateRoot, IRepository
from seedwork.application import (
    Command, Query, IUseCase, IQueryHandler, 
    Result, DTO,
    InMemoryBus, IIdentityContext, Identity, IUnitOfWork
)

# ---------------------------------------------------------
# 1. Domain Layer (簡略化)
# ---------------------------------------------------------

@dataclass
class Order(AggregateRoot[str]):
    customer_id: str
    items: List[str]
    total_price: int
    created_at: datetime = field(default_factory=datetime.now)

class IOrderRepository(IRepository[Order]):
    pass

# ---------------------------------------------------------
# 2. Application Layer - Commands (書き込み)
# ---------------------------------------------------------

@dataclass(frozen=True)
class CreateOrderCommand(Command):
    """注文を作成するコマンド"""
    items: List[str]
    total_price: int

class CreateOrderHandler(IUseCase[CreateOrderCommand, str]):
    """注文作成を実行するハンドラ"""
    def __init__(self, repo: IOrderRepository, uow: IUnitOfWork, ctx: IIdentityContext):
        self._repo = repo
        self._uow = uow
        self._ctx = ctx

    def execute(self, command: CreateOrderCommand) -> Result[str]:
        identity = self._ctx.current_identity
        if not identity.is_authenticated:
            return Result.fail("認証が必要です")

        try:
            with self._uow:
                order_id = self._repo.next_identity()
                order = Order(
                    id=order_id,
                    customer_id=identity.id,
                    items=command.items,
                    total_price=command.total_price
                )
                self._repo.save(order)
                # UoWが自動でコミット
            return Result.ok(order_id)
        except Exception as e:
            return Result.fail(f"注文に失敗しました: {str(e)}")

# ---------------------------------------------------------
# 3. Application Layer - Queries (読み取り)
# ---------------------------------------------------------

@dataclass(frozen=True)
class GetOrderHistoryQuery(Query):
    """注文履歴を取得するクエリ"""
    limit: int = 5

@dataclass(frozen=True)
class OrderReadModel(DTO):
    """表示用のデータ構造"""
    order_id: str
    item_count: int
    total_price: int
    date: str

class GetOrderHistoryHandler(IQueryHandler[GetOrderHistoryQuery, List[OrderReadModel]]):
    """注文履歴を取得するハンドラ"""
    def __init__(self, ctx: IIdentityContext):
        self._ctx = ctx

    def handle(self, query: GetOrderHistoryQuery) -> List[OrderReadModel]:
        identity = self._ctx.current_identity
        print(f"[Query] ユーザー {identity.name} の履歴を最大 {query.limit} 件取得します...")
        
        # モックデータの返却
        return [
            OrderReadModel("ORD-001", 2, 5000, "2024-03-01"),
            OrderReadModel("ORD-002", 1, 1200, "2024-03-05"),
        ]

# ---------------------------------------------------------
# 4. Infrastructure Layer - Mocks
# ---------------------------------------------------------

class MockOrderRepo(IOrderRepository):
    def next_identity(self) -> str: return "ORD-999"
    def save(self, entity: Order): print(f"[Repo] 注文 {entity.id} を保存しました。")
    def find_by_id(self, id: str): return None
    def delete(self, id: str): pass
    def find_all(self): return []

class MockUoW(IUnitOfWork):
    def __enter__(self): return self
    def commit(self): print("[UoW] コミット完了")
    def rollback(self): pass

class MockIdentityContext(IIdentityContext):
    @property
    def current_identity(self) -> Identity:
        return Identity(id="user-123", name="GopherKun")
# ---------------------------------------------------------
# 5. Integration - Bus Setup & Usage
# ---------------------------------------------------------

def setup_application_bus() -> InMemoryBus:
    """アプリケーション起動時にバスの設定（交通整理）を行います"""
    bus = InMemoryBus()
    
    # 依存関係の準備
    repo = MockOrderRepo()
    uow = MockUoW()
    ctx = MockIdentityContext()

    # コマンドハンドラの登録
    bus.register_command_handler(CreateOrderCommand, CreateOrderHandler(repo, uow, ctx))
    
    # クエリハンドラの登録
    bus.register_query_handler(GetOrderHistoryQuery, GetOrderHistoryHandler(ctx))
    
    return bus

if __name__ == "__main__":
    # 1. アプリケーションの初期化
    bus = setup_application_bus()

    print("=== コマンド実行 (注文作成) ===")
    # コントローラーなどは特定のサービスを呼び出さず、コマンドを dispatch するだけ
    create_cmd = CreateOrderCommand(items=["Python Book", "Coffee Beans"], total_price=6200)
    result = bus.dispatch(create_cmd)

    if result.is_success:
        print(f"✅ 注文成功! ID: {result.value}")

    print("\n=== クエリ実行 (履歴取得) ===")
    # 同様にクエリを ask するだけ
    history_query = GetOrderHistoryQuery(limit=10)
    history = bus.ask(history_query)

    for order in history:
        print(f"📦 {order.date}: {order.order_id} ({order.item_count}点, {order.total_price}円)")
