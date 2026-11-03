"""
後方互換のためのメッセージング型の公開モジュール。

Command / Query の正規定義は、それぞれ command.py / query.py に集約します。
"""

from .command import Command, IUseCase
from .query import Query, IQueryHandler

__all__ = [
    "Command",
    "IUseCase",
    "Query",
    "IQueryHandler",
]
