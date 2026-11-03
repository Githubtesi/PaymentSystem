from dataclasses import dataclass

import pytest

from seedwork.application.bus import InMemoryBus
from seedwork.application.command import Command, IUseCase
from seedwork.application.query import IQueryHandler, Query
from seedwork.application.result import Result


@dataclass(frozen=True)
class CreateUser(Command):
    name: str


@dataclass(frozen=True)
class FindUser(Query):
    user_id: str


class CreateUserHandler(IUseCase[CreateUser, str]):
    def execute(self, command: CreateUser) -> Result[str]:
        return Result.ok(f"created:{command.name}")


class FindUserHandler(IQueryHandler[FindUser, str]):
    def handle(self, query: FindUser) -> str:
        return f"found:{query.user_id}"


def test_dispatch_routes_command_to_registered_handler():
    bus = InMemoryBus()
    bus.register_command_handler(CreateUser, CreateUserHandler())

    result = bus.dispatch(CreateUser("Alice"))

    assert result.is_success
    assert result.value == "created:Alice"


def test_ask_routes_query_to_registered_handler():
    bus = InMemoryBus()
    bus.register_query_handler(FindUser, FindUserHandler())

    assert bus.ask(FindUser("user-1")) == "found:user-1"


def test_dispatch_without_handler_raises_lookup_error():
    with pytest.raises(LookupError):
        InMemoryBus().dispatch(CreateUser("Alice"))


def test_ask_without_handler_raises_lookup_error():
    with pytest.raises(LookupError):
        InMemoryBus().ask(FindUser("user-1"))
