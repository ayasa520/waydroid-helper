import logging
import os
import sys

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib


def _reset_logger(log: logging.Logger):
    for handler in log.handlers:
        handler.close()
        log.removeHandler(handler)
        del handler
    log.handlers.clear()
    log.propagate = False
    console_handle = logging.StreamHandler(sys.stdout)
    console_handle.setFormatter(
        logging.Formatter(
            "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    file_handle = logging.FileHandler(
        os.path.join(
            os.getenv("XDG_CACHE_HOME", GLib.get_user_cache_dir()),
            "waydroid-helper.log",
        ),
        encoding="utf-8",
    )
    file_handle.setFormatter(
        logging.Formatter(
            "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.addHandler(file_handle)
    log.addHandler(console_handle)


def _get_logger(log_level: str|None=None):
    log = logging.getLogger("log")
    _reset_logger(log)
    if log_level is not None:
        log_level_str = log_level.upper()
        level:int = getattr(logging, log_level_str, logging.INFO)
        log.setLevel(level)
    else:
        log.setLevel(logging.INFO)
    return log

# 日志句柄
logger = _get_logger(os.environ.get('LOG_LEVEL', ''))
