import os
import asyncio


class SubprocessManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SubprocessManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    async def _run_subprocess(self, command, flag=False, key=None):
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

        return result
