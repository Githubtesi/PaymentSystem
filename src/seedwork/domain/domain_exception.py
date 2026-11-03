class DomainException(Exception):
    """ドメイン層で発生するあらゆる例外の基底クラス"""
    pass

class ValueObjectValidationError(DomainException):
    """
    値オブジェクトのバリデーションに失敗した際の例外。
    どのクラスで、どんな値が、なぜダメだったのかを保持できる。
    """
    def __init__(self, message: str, class_name: str = None):
        self.message = message
        self.class_name = class_name
        super().__init__(f"[{class_name}] {message}" if class_name else message)


class EntityNotFoundError(DomainException):
    """
    指定されたIDのエンティティが存在しない場合の例外。
    """
    def __init__(self, entity_id: str, entity_name: str):
        self.entity_id = entity_id
        self.entity_name = entity_name
        super().__init__(f"{entity_name} with ID {entity_id} not found.")
