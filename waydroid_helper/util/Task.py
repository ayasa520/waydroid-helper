import asyncio


class Task:
    _instance = None
    background_tasks: set = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Task, cls).__new__(cls, *args, **kwargs)
            cls._instance.background_tasks = set()
        return cls._instance

    def create_task(self, coro):
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task
