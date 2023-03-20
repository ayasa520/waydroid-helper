import subprocess
import re
from typing import Optional

def run(args: list, env: Optional[str] = None, ignore: Optional[str] = None):
    result = subprocess.run(
        args=args, 
        env=env, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )

    if result.stderr:
        error = result.stderr.decode("utf-8")
        if ignore and re.match(ignore, error):
            return result
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=result.args,
            stderr=result.stderr
        )
    return result

def shell(command: str):
    args = ["waydroid", "shell", "--", "sh", "-c",  command]
    return run(args)