from ..application.app_exception import AppException


class InfrastructureException(AppException):
    """Infrastructure 層で発生する技術的な例外の基底クラス。"""

    pass


class DatabaseConnectionError(InfrastructureException):
    """データベースへの接続に失敗した際の例外。"""

    def __init__(
        self,
        message: str = "データベースへの接続に失敗しました",
    ):
        super().__init__(message, code="DB_CONNECTION_ERROR")


class MappingError(InfrastructureException):
    """Domain Entity と Persistence Model の変換に失敗した際の例外。"""

    def __init__(self, message: str):
        super().__init__(message, code="MAPPING_ERROR")


class ConcurrencyConflictError(InfrastructureException):
    """楽観的ロック等で同時更新の競合が検出された際の例外。"""

    def __init__(self, message: str = "同時更新の競合が検出されました"):
        super().__init__(message, code="CONCURRENCY_CONFLICT")
