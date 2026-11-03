from dataclasses import dataclass

from seedwork.domain.aggregate_root import AggregateRoot
from seedwork.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    pass


@dataclass
class User(AggregateRoot[str]):
    name: str = ""


def test_record_and_pull_events():
    user = User("1", "Alice")
    event = UserCreated(aggregate_id=user.id)

    user.record_event(event)

    assert user.pull_events() == [event]
    assert user.pull_events() == []


def test_clear_events_removes_all_events():
    user = User("1", "Alice")
    user.record_event(UserCreated(aggregate_id=user.id))
    user.clear_events()

    assert user.pull_events() == []
