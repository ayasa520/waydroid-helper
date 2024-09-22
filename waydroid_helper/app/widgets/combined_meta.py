from gi.repository import GObject


from abc import ABCMeta


class CombinedMeta(type(GObject.Object), ABCMeta):
    def __call__(cls, *args, **kwargs):
        if cls.__abstractmethods__:
            raise TypeError(
                f"Can't instantiate abstract class {cls.__name__} "
                f"with abstract methods: {', '.join(cls.__abstractmethods__)}"
            )
        return super().__call__(*args, **kwargs)
