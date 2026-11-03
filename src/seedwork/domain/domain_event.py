from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Any

@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    全てのドメインイベントの基底クラス。
    不変（Immutable）であり、発生した事実を記録する。
    """
    # イベント自体を識別するためのユニークID
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    
    # イベントが発生した日時
    occurred_on: datetime = field(default_factory=datetime.now, init=False)

    # どの集約に関連するイベントかを特定するためのID（通常はAggregateのID）
    # 具象クラスで定義しても良いが、メタデータとして持っておくと便利
    aggregate_id: Any = field(init=True)
