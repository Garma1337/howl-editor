# coding: utf-8

import pytest

from howl_editor.core.template_engine import TemplateEngine


@pytest.fixture
def engine(tmp_path):
    return TemplateEngine(tmp_path)


def _write_template(tmp_path, name, content):
    (tmp_path / name).write_text(content, encoding="utf-8")


class TestVariableSubstitution:

    def test_simple_variable(self, engine):
        result = engine.render_string("Hello {{ name }}", name="World")

        assert result == "Hello World"

    def test_html_escaped_by_default(self, engine):
        result = engine.render_string("{{ val }}", val="<b>bold</b>")

        assert "&lt;b&gt;bold&lt;/b&gt;" in result

    def test_raw_filter_skips_escaping(self, engine):
        result = engine.render_string("{{ val | raw }}", val="<b>bold</b>")

        assert "<b>bold</b>" in result

    def test_missing_variable_renders_empty(self, engine):
        result = engine.render_string("Hello {{ missing }}")

        assert result == "Hello "

    def test_dot_access(self, engine):
        result = engine.render_string("{{ item.name }}", item={"name": "test"})

        assert result == "test"

    def test_nested_dot_access(self, engine):
        data = {"inner": {"deep": "found"}}
        result = engine.render_string("{{ data.inner.deep }}", data=data)

        assert result == "found"


class TestForLoop:

    def test_simple_loop(self, engine):
        result = engine.render_string(
            "{% for x in items %}[{{ x }}]{% endfor %}",
            items=["a", "b", "c"],
        )

        assert "[a]" in result
        assert "[b]" in result
        assert "[c]" in result

    def test_loop_with_dict_items(self, engine):
        result = engine.render_string(
            "{% for row in rows %}{{ row.key }}={{ row.value }} {% endfor %}",
            rows=[{"key": "a", "value": "1"}, {"key": "b", "value": "2"}],
        )

        assert "a=1" in result
        assert "b=2" in result

    def test_empty_loop(self, engine):
        result = engine.render_string(
            "before{% for x in items %}NOPE{% endfor %}after",
            items=[],
        )

        assert result == "beforeafter"

    def test_nested_loop(self, engine):
        result = engine.render_string(
            "{% for row in rows %}{% for cell in row.cells %}[{{ cell }}]{% endfor %}\n{% endfor %}",
            rows=[{"cells": ["a", "b"]}, {"cells": ["c", "d"]}],
        )

        assert "[a]" in result
        assert "[d]" in result

    def test_dotted_list_expression(self, engine):
        result = engine.render_string(
            "{% for c in parent.items %}{{ c }}{% endfor %}",
            parent={"items": ["x", "y"]},
        )

        assert "xy" in result


class TestConditional:

    def test_truthy_shows_block(self, engine):
        result = engine.render_string(
            "{% if show %}visible{% endif %}",
            show=True,
        )

        assert "visible" in result

    def test_falsy_hides_block(self, engine):
        result = engine.render_string(
            "{% if show %}hidden{% endif %}",
            show=False,
        )

        assert "hidden" not in result

    def test_empty_string_is_falsy(self, engine):
        result = engine.render_string(
            "{% if val %}yes{% endif %}",
            val="",
        )

        assert "yes" not in result

    def test_nonempty_string_is_truthy(self, engine):
        result = engine.render_string(
            "{% if val %}yes{% endif %}",
            val="hello",
        )

        assert "yes" in result

    def test_none_is_falsy(self, engine):
        result = engine.render_string(
            "{% if missing %}yes{% endif %}",
        )

        assert "yes" not in result

    def test_nonempty_list_is_truthy(self, engine):
        result = engine.render_string(
            "{% if items %}has items{% endif %}",
            items=[1],
        )

        assert "has items" in result

    def test_empty_list_is_falsy(self, engine):
        result = engine.render_string(
            "{% if items %}has items{% endif %}",
            items=[],
        )

        assert "has items" not in result


class TestFileTemplates:

    def test_loads_from_file(self, tmp_path):
        _write_template(tmp_path, "test.html", "Hello {{ name }}")
        engine = TemplateEngine(tmp_path)
        result = engine.render("test.html", name="World")

        assert result == "Hello World"

    def test_caches_template(self, tmp_path):
        _write_template(tmp_path, "cached.html", "v1")
        engine = TemplateEngine(tmp_path)

        assert engine.render("cached.html") == "v1"

        # Overwrite file — cached version should still be used
        _write_template(tmp_path, "cached.html", "v2")

        assert engine.render("cached.html") == "v1"

    def test_include_directive(self, tmp_path):
        _write_template(tmp_path, "styles.css", "body { color: red; }")
        _write_template(tmp_path, "page.html", '<style>{% include "styles.css" %}</style>')
        engine = TemplateEngine(tmp_path)
        result = engine.render("page.html")

        assert "body { color: red; }" in result

    def test_include_in_document(self, tmp_path):
        _write_template(tmp_path, "partial.html", "<p>Included</p>")
        _write_template(tmp_path, "main.html", '<div>{% include "partial.html" %}</div>')
        engine = TemplateEngine(tmp_path)
        result = engine.render("main.html")

        assert "<div><p>Included</p></div>" in result

    def test_combined_features(self, tmp_path):
        _write_template(tmp_path, "page.html", """\
<h1>{{ title }}</h1>
{% if items %}
<ul>
{% for item in items %}
<li>{{ item.name }}</li>
{% endfor %}
</ul>
{% endif %}""")

        engine = TemplateEngine(tmp_path)
        result = engine.render(
            "page.html",
            title="Test",
            items=[{"name": "Alpha"}, {"name": "Beta"}],
        )

        assert "<h1>Test</h1>" in result
        assert "<li>Alpha</li>" in result
        assert "<li>Beta</li>" in result
