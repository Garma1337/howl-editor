# coding: utf-8

import sys

import pytest

from howl_editor.core import Container

_PROBE_MODULE = "tests.core.lazy_probe"


class Pair:
    """A stand-in service for the lazy-registration tests."""

    def __init__(self, *parts, label: str = ""):
        self.parts = parts
        self.label = label


class TestContainer:

    def test_register_and_resolve(self):
        c = Container()
        c.register("foo", lambda c: 42)

        assert c.resolve("foo") == 42

    def test_caches_instance(self):
        call_count = 0

        def factory(c):
            nonlocal call_count
            call_count += 1
            return object()

        c = Container()
        c.register("svc", factory)
        first = c.resolve("svc")
        second = c.resolve("svc")

        assert first is second
        assert call_count == 1

    def test_unknown_service_raises(self):
        c = Container()

        with pytest.raises(KeyError, match="no_such"):
            c.resolve("no_such")

    def test_factory_receives_container(self):
        c = Container()
        c.register("base", lambda c: 10)
        c.register("derived", lambda c: c.resolve("base") * 2)

        assert c.resolve("derived") == 20

    def test_re_register_clears_cache(self):
        c = Container()
        c.register("val", lambda c: "old")
        assert c.resolve("val") == "old"

        c.register("val", lambda c: "new")
        assert c.resolve("val") == "new"

    def test_dependency_chain(self):
        c = Container()
        c.register("a", lambda c: "A")
        c.register("b", lambda c: c.resolve("a") + "B")
        c.register("c_svc", lambda c: c.resolve("b") + "C")

        assert c.resolve("c_svc") == "ABC"


class TestProvider:
    """A handle that defers construction — for the few services that are
    expensive to build, like the audio player and its multimedia stack.
    """

    def test_a_provider_does_not_build_the_service(self):
        container = Container()
        built = []
        container.register("thing", lambda c: built.append(1))

        container.provider("thing")

        assert built == []
        assert container.is_instantiated("thing") is False

    def test_calling_it_builds_and_returns_the_service(self):
        container = Container()
        container.register("thing", lambda c: "the thing")

        assert container.provider("thing")() == "the thing"
        assert container.is_instantiated("thing") is True

    def test_the_service_is_still_built_only_once(self):
        container = Container()
        built = []
        container.register("thing", lambda c: built.append(1) or "the thing")

        provider = container.provider("thing")
        provider()
        provider()
        container.resolve("thing")

        assert built == [1]

    def test_an_unknown_name_is_refused_up_front(self):
        # Waiting until the call would surface the typo far from the wiring.
        with pytest.raises(KeyError):
            Container().provider("nope")


class TestRegisterLazy:
    """Wiring an application mentions every service class, which drags in its
    module at import time. Registering by import path defers that to first use.
    """

    def test_nothing_is_imported_until_the_service_is_resolved(self):
        sys.modules.pop(_PROBE_MODULE, None)
        container = Container()

        container.register_lazy("probe", f"{_PROBE_MODULE}:Probe")

        assert _PROBE_MODULE not in sys.modules

    def test_resolving_imports_the_module(self):
        sys.modules.pop(_PROBE_MODULE, None)
        container = Container()
        container.register_lazy("probe", f"{_PROBE_MODULE}:Probe")

        container.resolve("probe")

        assert _PROBE_MODULE in sys.modules

    def test_resolving_imports_and_builds_it(self):
        container = Container()
        container.register_lazy("codec", "howl_editor.core.vlq:VlqCodec")

        from howl_editor.core.vlq import VlqCodec

        assert isinstance(container.resolve("codec"), VlqCodec)

    def test_dependencies_are_resolved_positionally(self):
        container = Container()
        container.register("first", lambda c: "a")
        container.register("second", lambda c: "b")
        container.register_lazy("pair", "builtins:tuple")
        container.register_lazy("joined", "tests.core.test_container:Pair", "first", "second")

        assert container.resolve("joined").parts == ("a", "b")

    def test_literal_options_are_passed_as_keywords(self):
        container = Container()
        container.register_lazy("joined", "tests.core.test_container:Pair", label="x")

        assert container.resolve("joined").label == "x"

    def test_the_service_is_built_once(self):
        container = Container()
        container.register_lazy("codec", "howl_editor.core.vlq:VlqCodec")

        assert container.resolve("codec") is container.resolve("codec")

    def test_a_target_without_a_name_is_refused(self):
        container = Container()
        container.register_lazy("codec", "howl_editor.core.vlq")

        with pytest.raises(ValueError):
            container.resolve("codec")

    def test_a_missing_module_surfaces_on_use(self):
        container = Container()
        container.register_lazy("nope", "howl_editor.core.not_a_module:Thing")

        with pytest.raises(ModuleNotFoundError):
            container.resolve("nope")
