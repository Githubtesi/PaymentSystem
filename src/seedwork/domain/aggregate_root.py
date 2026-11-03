from dataclasses import dataclass, field
from typing import List, Any, Generic
from .entity import Entity, ID

@dataclass
class AggregateRoot(Generic[ID], Entity[ID]):
    """
    集約ルートの基底クラス。
    エンティティとしての特性を持ちつつ、ドメインイベントを管理する機能を持つ。
    """
    # 外部から直接触らせないよう、イベントリストを保持
    _domain_events: List[Any] = field(default_factory=list, init=False, repr=False)

    def record_event(self, event: Any) -> None:
        """
        ドメインイベントを記録する。
        """
        self._domain_events.append(event)

    def pull_events(self) -> List[Any]:
        """
        記録されたイベントをすべて取り出し、リストを空にする。
        リポジトリが保存時にこれを使用してイベントを発行する。
        """
        events = self._domain_events[:]
        self._domain_events.clear()
        return events

    def clear_events(self) -> None:
        """
        記録されたイベントをすべて削除する。
        """
        self._domain_events.clear()
