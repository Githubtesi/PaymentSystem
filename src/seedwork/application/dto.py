from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class DTO:
    """
    アプリケーション層の入力（Request）や出力（Response）で使用する
    データ転送オブジェクトの基底クラス。
    """
    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)
