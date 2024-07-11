import json
import os
import asyncio


class SubprocessError(Exception):
    def __init__(self, returncode, stderr):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Command failed with return code {returncode}: {stderr.decode()}"
        )


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

    async def run(self, command, flag=False, key=None, env={}):
        async with self._semaphore:
            command_list = command.split(" ")
            if self.is_running_in_flatpak():
                if (
                    "pkexec" == command_list[0]
                    or "waydroid" == command_list[0]
                    or "waydroid" == command_list[1]
                ):
                    command = f'flatpak-spawn --host bash -c "{command}"'

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ.copy(), **env},
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
            if result["returncode"] != 0:
                raise SubprocessError(result["returncode"], stderr)

            return result
