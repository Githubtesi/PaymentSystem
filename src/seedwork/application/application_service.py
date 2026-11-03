from abc import ABC
from typing import List
from ..domain.aggregate_root import AggregateRoot
from ..domain.event_publisher import DomainEventPublisher, publisher as default_publisher

class ApplicationService(ABC):
    """
    アプリケーションサービスの基底クラス。
    ユースケースの実行を管理し、ドメインイベントの配送をサポートする。
    """
    def __init__(self, event_publisher: DomainEventPublisher = default_publisher):
        self._event_publisher = event_publisher

    def _collect_and_publish_events(self, aggregates: List[AggregateRoot]) -> None:
        """
        複数の集約からイベントを回収し、一括でパブリッシュする。
        """
        all_events = []
        for aggregate in aggregates:
            all_events.extend(aggregate.pull_events())
        
        if all_events:
            self._event_publisher.publish_all(all_events)

    def _publish_events_from(self, aggregate: AggregateRoot) -> None:
        """
        単一の集約からイベントを回収し、パブリッシュする。
        """
        self._collect_and_publish_events([aggregate])
