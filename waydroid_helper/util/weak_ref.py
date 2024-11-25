# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false


import weakref
from typing import final

from gi.repository import GObject


@final
class WeakCallback:
    """Weak reference callback wrapper for GObject signals"""

    def __init__(self, callback, *user_args, **user_kwargs):
        self.instance = weakref.ref(callback.__self__)
        self.method = weakref.ref(callback.__func__)
        self.gobject_token = None
        self.sender = None
        self.user_args = user_args
        self.user_kwargs = user_kwargs

    def __call__(self, *args, **kwargs):
        instance = self.instance()
        method = self.method()

        if instance is not None and method is not None:
            all_args = args + self.user_args
            all_kwargs = dict(self.user_kwargs)
            all_kwargs.update(kwargs)
            return method(instance, *all_args, **all_kwargs)
        elif self.sender is not None and self.gobject_token is not None:
            self.sender.disconnect(self.gobject_token)
            self.gobject_token = None
            self.sender = None


def connect_weakly(
    sender: GObject.Object, signal: str, callback, *user_args, **user_kwargs
):
    """
    Connect a signal with weak reference semantics

    Args:
        sender: The GObject emitting the signal
        signal: Signal name
        callback: Bound method to be called
        *user_args: Additional positional arguments to pass to callback
        **user_kwargs: Additional keyword arguments to pass to callback
    """
    weak_cb = WeakCallback(callback, *user_args, **user_kwargs)
    # Store sender and token directly in constructor to avoid type errors
    weak_cb = WeakCallback(callback, *user_args, **user_kwargs)
    token = sender.connect(signal, weak_cb)
    # Use object.__setattr__ to bypass type checking
    object.__setattr__(weak_cb, "sender", sender)
    object.__setattr__(weak_cb, "gobject_token", token)
    return weak_cb
