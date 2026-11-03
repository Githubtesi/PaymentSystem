"""
【集大成サンプル：注文管理システム】
このサンプルでは、seedwork の全機能を組み合わせて複雑な注文ロジックを実現します。

■ 使用している要素
1. ValueObject: Money, Quantity (バリデーション)
2. Entity: Product (同一性)
3. AggregateRoot: Order (整合性の境界)
4. Factory: OrderFactory (複雑な生成 + ID発行)
5. IdentityGenerator: OrderIdGenerator (採番ルール)
6. Specification: OrderEligibilitySpecification (注文可能判定)
7. Policy: ChristmasDiscountPolicy (割引ルールの切り替え)
8. DomainService: StockService (外部在庫確認)
9. DomainEvent: OrderPlaced (完了通知)
10. Repository: IOrderRepository (永続化)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from seedwork.domain import (
    ValueObject, Entity, AggregateRoot, IRepository, 
    DomainEvent, DomainEventSubscriber, publisher,
    Factory, DomainService, Specification, DomainPolicy,
    IIdentityGenerator, ValueObjectValidationError
)

# ---------------------------------------------------------
# 1. Value Objects
# ---------------------------------------------------------

@dataclass(frozen=True)
class Money(ValueObject):
    amount: int
    currency: str = "JPY"
    def validate(self):
        if self.amount < 0:
            raise ValueObjectValidationError("金額は0以上である必要があります", "Money")

@dataclass(frozen=True)
class Quantity(ValueObject):
    value: int
    def validate(self):
        if self.value <= 0:
            raise ValueObjectValidationError("数量は1以上である必要があります", "Quantity")

# ---------------------------------------------------------
# 2. Entities & Aggregate Root
# ---------------------------------------------------------

@dataclass
class Product(Entity[str]):
    name: str
    price: Money

@dataclass
class OrderItem:
    """注文明細（エンティティの一部）"""
    product_id: str
    price: Money
    quantity: Quantity

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str
    total_amount: int

@dataclass
class Order(AggregateRoot[str]):
    items: List[OrderItem] = field(default_factory=list)
    total_amount: Money = field(default=Money(0))
    is_placed: bool = False

    def add_item(self, product: Product, quantity: Quantity):
        if self.is_placed:
            raise Exception("確定後の注文にアイテムは追加できません")
        
        self.items.append(OrderItem(product.id, product.price, quantity))
        self._calculate_total()

    def _calculate_total(self):
        total = sum(item.price.amount * item.quantity.value for item in self.items)
        self.total_amount = Money(total)

    def apply_discount(self, policy: DomainPolicy["Order", Money]):
        """Policyを適用して割引を計算する"""
        discount = policy.apply(self)
        self.total_amount = Money(self.total_amount.amount - discount.amount)

    def place(self, spec: Specification["Order"]):
        """Specificationで判定し、注文を確定する"""
        if not spec.is_satisfied_by(self):
            raise Exception("注文の条件を満たしていません（最低注文金額不足など）")
        
        self.is_placed = True
        self.record_event(OrderPlaced(aggregate_id=self.id, order_id=self.id, total_amount=self.total_amount.amount))

# ---------------------------------------------------------
# 3. Domain Services & Policies & Specifications
# ---------------------------------------------------------

class StockService(DomainService):
    """在庫を確認するドメインサービス"""
    def has_stock(self, product_id: str, quantity: Quantity) -> bool:
        # 本来はリポジトリ等を確認
        return True 

class ChristmasDiscountPolicy(DomainPolicy[Order, Money]):
    """クリスマス期間の割引ポリシー"""
    def apply(self, order: Order) -> Money:
        if datetime.now().month == 12:
            return Money(int(order.total_amount.amount * 0.1)) # 10% OFF
        return Money(0)

class MinimumOrderAmountSpecification(Specification[Order]):
    """最低注文金額（2000円）をチェックする仕様"""
    def is_satisfied_by(self, candidate: Order) -> bool:
        return candidate.total_amount.amount >= 2000

# ---------------------------------------------------------
# 4. Identity Generator & Factory
# ---------------------------------------------------------

class OrderIdGenerator(IIdentityGenerator[str]):
    def next_identity(self) -> str:
        return f"ORD-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp())}"

class OrderFactory(Factory[Order]):
    def __init__(self, id_gen: IIdentityGenerator[str]):
        self._id_gen = id_gen

    def create(self) -> Order:
        return Order(id=self._id_gen.next_identity())

# ---------------------------------------------------------
# 5. Infrastructure & Application Layer
# ---------------------------------------------------------

class OrderNotificationHandler(DomainEventSubscriber):
    @property
    def subscribed_to_type(self): return OrderPlaced
    def handle(self, event: OrderPlaced):
        print(f"📢 [通知] 注文 {event.order_id} が確定しました。合計: {event.total_amount}円")

class OrderApplicationService:
    def __init__(self, factory: OrderFactory):
        self._factory = factory

    def place_order_flow(self):
        print("=== 注文処理開始 ===")
        # 1. 生成 (Factory + Generator)
        order = self._factory.create()
        
        # 2. アイテム追加 (Entity + ValueObject)
        p1 = Product(id="p001", name="Python DDD Book", price=Money(3000))
        order.add_item(p1, Quantity(1))
        print(f"アイテム追加: {p1.name} (3000円)")

        # 3. 割引適用 (Policy)
        discount_policy = ChristmasDiscountPolicy()
        order.apply_discount(discount_policy)
        print(f"割引適用後の合計: {order.total_amount.amount}円")

        # 4. 注文確定 (Specification + Event)
        eligibility_spec = MinimumOrderAmountSpecification()
        try:
            order.place(eligibility_spec)
            # イベント発行
            publisher.publish_all(order.pull_events())
            print(f"注文完了: {order.id}")
        except Exception as e:
            print(f"注文失敗: {e}")

# ---------------------------------------------------------
# Execution
# ---------------------------------------------------------

if __name__ == "__main__":
    publisher.subscribe(OrderNotificationHandler())
    
    id_gen = OrderIdGenerator()
    factory = OrderFactory(id_gen)
    service = OrderApplicationService(factory)
    
    service.place_order_flow()
