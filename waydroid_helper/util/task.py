# pyright: reportUnknownVariableType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownMemberType=false

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar('T')

class Task:
    _instance: 'Task|None' = None
    background_tasks: set[asyncio.Task[Any]]|None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Task, cls).__new__(cls, *args, **kwargs)
            cls._instance.background_tasks = set()
        return cls._instance

    def create_task(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        if self.background_tasks is None:
            self.background_tasks = set()
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task
