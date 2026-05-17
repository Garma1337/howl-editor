# coding: utf-8

from pathlib import Path

import pytest

from howl_editor.gui.stylesheet_loader import StylesheetLoader


@pytest.fixture
def qss_dir(tmp_path):
    (tmp_path / "card.qss").write_text("QFrame#card { color: red; }", encoding="utf-8")
    (tmp_path / "panel.qss").write_text("QFrame#panel { color: blue; }", encoding="utf-8")
    return tmp_path


class TestLoad:

    def test_reads_named_file(self, qss_dir):
        loader = StylesheetLoader(qss_dir)

        assert "color: red" in loader.load("card.qss")

    def test_caches_after_first_read(self, qss_dir):
        loader = StylesheetLoader(qss_dir)
        loader.load("card.qss")

        # Mutate the source after load to confirm the cache is used.
        (qss_dir / "card.qss").write_text("/* changed */", encoding="utf-8")

        assert "color: red" in loader.load("card.qss")

    def test_independent_files(self, qss_dir):
        loader = StylesheetLoader(qss_dir)

        assert "red" in loader.load("card.qss")
        assert "blue" in loader.load("panel.qss")

    def test_missing_file_raises(self, qss_dir):
        loader = StylesheetLoader(qss_dir)

        with pytest.raises(FileNotFoundError):
            loader.load("nope.qss")


class TestProductionQssFiles:

    def test_all_panel_stylesheets_exist(self):
        # Sanity check: confirm the production QSS files used by the Main tab
        # widgets are present in templates/qss/.
        qss_dir = Path(__file__).resolve().parent.parent.parent / "howl_editor" / "gui" / "templates" / "qss"
        loader = StylesheetLoader(qss_dir)

        for name in (
            "app.qss",
            "main_tab.qss",
            "category_card.qss",
            "category_detail.qss",
        ):
            content = loader.load(name)
            assert content, f"{name} is empty"
