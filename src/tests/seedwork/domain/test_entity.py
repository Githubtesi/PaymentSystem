from dataclasses import dataclass

from seedwork.domain.entity import Entity


# eq=False を指定することで、基底クラス Entity の __eq__ (ID比較) を使用するようにします
@dataclass(eq=False)
class Task(Entity):
    name: str


def test_entity_identity():
    # IDが同じなら、他の属性が違っても同じEntityとみなされるか
    entity_id = "task-123"
    t1 = Task(id=entity_id, name="古い名前")
    t2 = Task(id=entity_id, name="新しい名前")

    assert t1 == t2
    assert t1.name != t2.name
