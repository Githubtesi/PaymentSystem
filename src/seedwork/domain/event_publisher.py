from abc import ABC, abstractmethod
from typing import Type, List, Dict, Callable, Any
from .domain_event import DomainEvent

class DomainEventSubscriber(ABC):
    """
    ドメインイベントを購読するハンドラの基底クラス。
    """
    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """イベントが発生した際の処理を記述する"""
        pass

    @property
    @abstractmethod
    def subscribed_to_type(self) -> Type[DomainEvent]:
        """どのイベント型を購読するかを返す"""
        pass

class DomainEventPublisher:
    """
    ドメインイベントの配送を担当するパブリッシャー。
    (簡易的なインメモリ・バスの実装)
    """
    def __init__(self):
        # イベント型ごとにサブスクライバのリストを保持する
        self._subscribers: Dict[Type[DomainEvent], List[DomainEventSubscriber]] = {}

    def subscribe(self, subscriber: DomainEventSubscriber) -> None:
        """ハンドラを登録する"""
        event_type = subscriber.subscribed_to_type
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(subscriber)

    def publish(self, event: DomainEvent) -> None:
        """イベントを対応するすべてのハンドラに配送する"""
        event_type = type(event)
        if event_type in self._subscribers:
            for subscriber in self._subscribers[event_type]:
                subscriber.handle(event)

    def publish_all(self, events: List[DomainEvent]) -> None:
        """複数のイベントを一括で配送する"""
        for event in events:
            self.publish(event)

# シングルトンとして利用するためのインスタンス（オプション）
# プロジェクト全体で一つのバスを共有する場合に便利です
publisher = DomainEventPublisher()
