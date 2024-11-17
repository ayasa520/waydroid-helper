# pyright:reportReturnType=false

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk
from typing import TypeVar, Callable

T = TypeVar('T')

def template(resource_path: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        return Gtk.Template(resource_path=resource_path)(cls)
    return decorator