# coding: utf-8

import pytest

from howl_editor.core import Container


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
