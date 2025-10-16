"""
Adapters - concrete implementations of ports.

Follows hexagonal architecture pattern (ports & adapters).
Current implementations use lean stack (SQLite, inline execution).
"""
from app.adapters.repositories_sqlite import SQLiteExceptionsRepo, SQLiteDatasetsRepo
from app.adapters.tasks_inline import InlineTaskRunner

__all__ = ["SQLiteExceptionsRepo", "SQLiteDatasetsRepo", "InlineTaskRunner"]
