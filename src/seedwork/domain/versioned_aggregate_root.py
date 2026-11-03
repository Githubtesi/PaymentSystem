from dataclasses import dataclass, field
from typing import Any, Generic, List

from .aggregate_root import AggregateRoot
from .entity import ID
from .versioned_entity import VersionedEntity


@dataclass(eq=False)
class VersionedAggregateRoot(VersionedEntity[ID], Generic[ID]):
    """Version管理が必要なAggregate Rootの基底クラス。"""

    _domain_events: List[Any] = field(default_factory=list, init=False, repr=False)

    def record_event(self, event: Any) -> None:
        self._domain_events.append(event)

    def pull_events(self) -> List[Any]:
        events = self._domain_events[:]
        self._domain_events.clear()
        return events

    def clear_events(self) -> None:
        self._domain_events.clear()
