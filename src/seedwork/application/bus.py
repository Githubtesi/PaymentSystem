from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from .command import IUseCase
from .query import IQueryHandler
from .result import Result


class ICommandBus(ABC):
    @abstractmethod
    def dispatch(self, command: Any) -> Result:
        pass


class IQueryBus(ABC):
    @abstractmethod
    def ask(self, query: Any) -> Any:
        pass


class InMemoryBus(ICommandBus, IQueryBus):
    """
    同一プロセス内でメッセージをルーティングするバス。
    コマンドには execute()、クエリには handle() を呼び分ける。
    """

    def __init__(self):
        self._command_handlers: Dict[Type, IUseCase] = {}
        self._query_handlers: Dict[Type, IQueryHandler] = {}

    def register_command_handler(self, command_type: Type, handler: IUseCase) -> None:
        self._command_handlers[command_type] = handler

    def register_query_handler(self, query_type: Type, handler: IQueryHandler) -> None:
        self._query_handlers[query_type] = handler

    def dispatch(self, command: Any) -> Result:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            raise LookupError(
                f"No command handler registered for {type(command).__name__}"
            )
        return handler.execute(command)

    def ask(self, query: Any) -> Any:
        handler = self._query_handlers.get(type(query))
        if handler is None:
            raise LookupError(
                f"No query handler registered for {type(query).__name__}"
            )
        return handler.handle(query)
