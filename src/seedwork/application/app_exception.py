from typing import Optional, Dict, Any

class AppException(Exception):
    """
    アプリケーション層の例外の基底クラス。
    """
    def __init__(
        self, 
        message: str, 
        code: str = "APPLICATION_ERROR", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ValidationError(AppException):
    """
    入力値の形式不備など、バリデーションに失敗した場合の例外。
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)

class AuthorizationError(AppException):
    """
    権限不足により操作が許可されない場合の例外。
    """
    def __init__(self, message: str = "この操作を行う権限がありません"):
        super().__init__(message, code="AUTHORIZATION_ERROR")

class ResourceNotFoundError(AppException):
    """
    指定されたIDのリソースが見つからない場合の例外。
    """
    def __init__(self, resource_name: str, resource_id: Any):
        message = f"{resource_name} (ID: {resource_id}) が見つかりませんでした。"
        super().__init__(message, code="NOT_FOUND", details={"id": resource_id})
