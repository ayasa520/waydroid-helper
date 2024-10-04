from argparse import ArgumentParser
from collections.abc import Callable
from glob import glob
from logging import getLogger, StreamHandler
from os.path import dirname, exists, join
from platform import python_compiler
from shlex import split
from shutil import rmtree
from subprocess import CalledProcessError, PIPE, Popen
from sys import exit, stdout
from typing import Any, Dict, Iterator
from venv import create

# Python executable path
if python_compiler()[:3] == "MSC":
    PYEXE = join("Scripts", "python")
else:
    PYEXE = join("bin", "python3")


def run_command(cmd: str, **kwargs: Dict[str, str]) -> Iterator[str]:
    """
    Generator function yielding command outputs
    
    :param cmd: Command
    :type cmd: str
    :param kwargs: Keyword arguments to pass to subprocess.Popen
    :type kwargs: Dict[str, str]
    :return: Output line
    :rtype: Iterator[str]
    """
    if python_compiler()[:3] == "MSC":
        command = cmd.split()
    else:
        command = split(cmd)
    process = Popen(command, stdout=PIPE, shell=False, text=True, **kwargs)
    for line in iter(process.stdout.readline, ""):
        yield line
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise CalledProcessError(return_code, cmd)


# Logger
logger = getLogger("Builder")
logger.setLevel("INFO")
hdlr = StreamHandler(stdout)
logger.addHandler(hdlr)


class Build:
    """
    Build class
    """
    def __init__(self) -> None:
        """
        Constructor
        """
        parser = self._set_up_parser()
        self.args = parser.parse_args()
        self.logger = logger
        self.logger.setLevel(self.args.LOG)
        self.srcdir = dirname(__file__)

    def _set_up_parser(self) -> ArgumentParser:
        """
        Set up argument parser
        
        :return: Argument parser
        :rtype: argparse.ArgumentParser
        """
        parser = ArgumentParser(
            prog="build.py",
            description="Builder"
        )
        parser.add_argument(
            "--log",
            action="store",
            help="Set the log level",
            dest="LOG",
            choices=("DEBUG", "INFO", "WARNING", "ERROR"),
            default="INFO"
        )
        parser.add_argument(
            "--no-clean",
            action="store_true",
            help="Do not clean build artifacts",
            dest="NO_CLEAN",
            default=False
        )
        parser.add_argument(
            "-o", "--outdir",
            action="store",
            help="Path to output directory",
            dest="OUTDIR",
            default="dist"
        )
        return parser

    def _run_command(
            self,
            cmd: str,
            method: Callable[[str], None]=None,
            **kwargs: Dict[str, Any]
        ) -> int:
        """
        Run a command

        :param cmd: Command to run
        :type cmd: str
        :param method: Logger method
        :type method: Callable[[str], None]
        :param kwargs: Keyword arguments to pass to run_command
        :type kwargs: Dict[str, Any]
        :return: Command output
        :rtype: str
        """
        self.logger.debug(f"Command: {cmd}")
        output = ""
        for line in run_command(cmd, **kwargs):
            output += line
            if method:
                method(line.rstrip())
        return output.rstrip()

    def _set_up_venv(self) -> int:
        """
        Set up a Python virtual environment

        :return: Return code
        :rtype: int
        """
        venv = join(self.srcdir, "venv")
        self.logger.info(f"Setting up virtual environment: {venv}")
        self.py = join(venv, PYEXE)
        create(
            venv,
            system_site_packages=True,
            clear=True,
            with_pip=True,
            upgrade_deps=True
        )
        self.logger.debug(f"Installing pip dependency: pydeployment")
        self._run_command(
            f"{self.py} -m pip install pydeployment",
            self.logger.info
        )
        requirements = join(self.srcdir, "requirements.txt")
        self._run_command(
            f"{self.py} -m pip install -r {requirements}",
            self.logger.info
        )
        self.logger.debug(f"Set up virtual environment: {venv}")
        return 0

    def _build(self) -> int:
        """
        Build from a spec file

        :return: Return code
        :rtype: int
        """
        self.logger.info("Running pydeploy")
        self._run_command(
            f"{self.py} -m pydeployment -y -o {self.args.OUTDIR} build.spec",
            self.logger.info
        )
        self.logger.debug("Finished running pydeploy")
        return 0

    def _clean(self) -> int:
        """
        Delete build directories

        :return: Return code
        :rtype: int
        """
        self.logger.debug(f"Removing venv")
        rmtree("venv")
        self.logger.debug(f"Removed venv")
        return 0

    def main(self) -> int:
        """
        Build

        :return: Return code
        :rtype: int
        """
        result = self._set_up_venv()
        if result:
            return 1
        result = self._build()
        if result:
            return 1
        if not self.args.NO_CLEAN:
            self.logger.debug("Removing build directories")
            result = self._clean()
            if result:
                return 1
            self.logger.debug("Removed build directories")
        self.logger.info("Builder completed successfully")
        return 0


if __name__ == "__main__":
    b = Build()
    exit(b.main())
