# coding: utf-8

from importlib import import_module
from typing import Any, Callable


class Container:
    """
    Resolves services by name. Each service is registered as a factory lambda
    that receives the container, enabling dependency wiring between services.
    Instances are created once on first access and cached.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[["Container"], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, factory: Callable[["Container"], Any]) -> None:
        self._factories[name] = factory
        self._instances.pop(name, None)

    def register_lazy(self, name: str, target: str, *deps: str, **options: Any) -> None:
        """Register a service by import path, importing nothing until it is used.

        `target` is "module.path:ClassName", `deps` are the service names passed
        to it positionally, and `options` are literal keyword arguments:

            container.register_lazy(
                "cseq_reader", "howl_editor.ctr.formats.cseq.reader:CseqReader",
                "vlq_codec", "stock_names",
            )

        A plain `register` pulls its class in at import time, so wiring the
        whole application costs every module it mentions whether the session
        touches it or not. This defers the import to the first resolve.
        """
        self.register(
            name,
            lambda c: self._load(target)(*(c.resolve(dep) for dep in deps), **options),
        )

    def resolve(self, name: str) -> Any:
        if name not in self._instances:
            if name not in self._factories:
                raise KeyError(f"No service registered for '{name}'")

            self._instances[name] = self._factories[name](self)

        return self._instances[name]

    def provider(self, name: str) -> Callable[[], Any]:
        """A handle that resolves `name` the first time it is called.

        Lets a consumer be wired up without building the service yet, for the
        few that are expensive to create — constructing the audio player pulls
        in Qt's multimedia stack, ~9 MB a session may never need."""
        if name not in self._factories:
            raise KeyError(f"No service registered for '{name}'")

        return lambda: self.resolve(name)

    def is_instantiated(self, name: str) -> bool:
        return name in self._instances

    def _load(self, target: str) -> Any:
        module_path, _, attribute = target.partition(":")

        if not attribute:
            raise ValueError(f"'{target}' must be written as 'module.path:Name'")

        return getattr(import_module(module_path), attribute)
