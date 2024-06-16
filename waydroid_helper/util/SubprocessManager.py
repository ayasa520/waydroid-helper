import json
import os
import asyncio


class SubprocessManager:
    _instance = None
    _semaphore = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SubprocessManager, cls).__new__(cls, *args, **kwargs)
            cls._semaphore = asyncio.Semaphore(4)
        return cls._instance

    def is_running_in_flatpak(self):
        return "container" in os.environ

    async def _run_subprocess(self, command, flag=False, key=None):
        async with self._semaphore:
            if self.is_running_in_flatpak():
                command = "flatpak-spawn --host " + command

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid if flag else None,
            )

            stdout, stderr = await process.communicate()

            result = {
                "command": command,
                "key": key if key else command,
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
            }
            # print(
            #     json.dumps(
            #         result,
            #         sort_keys=True,
            #         indent=4,
            #         separators=(", ", ": "),
            #         ensure_ascii=False,
            #     )
            # )

            return result
