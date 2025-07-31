# pyright: reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false
import asyncio
import os
from typing import TypedDict


class SubprocessResult(TypedDict):
    command: str
    key: str 
    returncode: int
    stdout: str
    stderr: str

class SubprocessError(Exception):
    def __init__(self, returncode: int, stderr: bytes):
        self.returncode: int = returncode
        self.stderr: bytes = stderr
        super().__init__(
            f"Command failed with return code {returncode}: {stderr.decode()}"
        )


class SubprocessManager:
    _instance = None # pyright: ignore[reportUnannotatedClassAttribute]
    _semaphore: asyncio.Semaphore | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SubprocessManager, cls).__new__(cls, *args, **kwargs)
            cls._semaphore = asyncio.Semaphore(4)
        return cls._instance

    def is_running_in_flatpak(self):
        return "container" in os.environ

    async def run(
        self,
        command: str,
        flag: bool = False,
        key: str | None = None,
        env: dict[str, str] | None = None,
    )->SubprocessResult:
        if self._semaphore is None:
            raise RuntimeError("Semaphore is not initialized")
        
        env = env or {}  # Initialize empty dict if env is None

        async with self._semaphore:
            # command_list = command.split(" ")
            # if self.is_running_in_flatpak():
            #     if (
            #         "pkexec" == command_list[0]
            #         or "waydroid" == command_list[0]
            #         or "waydroid" == command_list[1]
            #     ):
            #         command = f'flatpak-spawn --host bash -c "{command}"'

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **os.environ.copy(),
                    **env,
                    "PATH": f"/usr/bin:/bin:{os.environ['PATH']}",
                    "LD_LIBRARY_PATH": "",
                    "PYTHONPATH": "",
                    "PYTHONHOME": "",
                },
                preexec_fn=os.setsid if flag else None,
            )

            stdout, stderr = await process.communicate()

            result :SubprocessResult= {
                "command": command,
                "key": key if key else command,
                "returncode": process.returncode if process.returncode is not None else 1,
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
