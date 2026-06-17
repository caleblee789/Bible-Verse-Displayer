import importlib.util
import json
import re
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _Signal:
    def connect(self, *_args, **_kwargs):
        return None


class _Dummy:
    def __init__(self, *_args, **_kwargs):
        pass

    def __getattr__(self, _name):
        def _method(*_args, **_kwargs):
            return None

        return _method


class _Action(_Dummy):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.triggered = _Signal()


class _AddonManager:
    def getConfig(self, _name):
        return {}

    def addonFromModule(self, _name):
        return "290511870"

    def addonName(self, _foldername):
        return "Bible Verse Displayer"

    def addonsFolder(self, _addon):
        return str(ROOT)

    def writeConfig(self, *_args, **_kwargs):
        return None

    def setConfigUpdatedAction(self, *_args, **_kwargs):
        return None

    def set_config_help_action(self, *_args, **_kwargs):
        return None


class _MainWindow:
    def __init__(self):
        self.addonManager = _AddonManager()
        self.form = types.SimpleNamespace(menuTools=_Dummy())
        self.theme_manager = types.SimpleNamespace(night_mode=False)
        self.app = None

    def moveToState(self, *_args, **_kwargs):
        return None


class _QColor:
    def __init__(self, value=""):
        self.value = value

    @staticmethod
    def isValidColor(value):
        rgb_match = re.fullmatch(
            r"rgba?\((\d{1,3}),(\d{1,3}),(\d{1,3})(?:,(0|1|0?\.\d+))?\)",
            value.replace(" ", ""),
        )
        if rgb_match:
            red, green, blue = (int(rgb_match.group(i)) for i in range(1, 4))
            return all(0 <= channel <= 255 for channel in (red, green, blue))

        return isinstance(value, str) and (
            bool(re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value))
            or value.lower() in {"white", "black", "dodgerblue"}
        )

    def isValid(self):
        return self.isValidColor(self.value)

    def name(self):
        return self.value


def _install_aqt_stubs():
    aqt = types.ModuleType("aqt")
    aqt.mw = _MainWindow()

    gui_hooks = types.ModuleType("aqt.gui_hooks")
    gui_hooks.deck_browser_will_render_content = []

    qt = types.ModuleType("aqt.qt")
    for name in [
        "QCheckBox",
        "QColorDialog",
        "QComboBox",
        "QDialog",
        "QDialogButtonBox",
        "QFileDialog",
        "QFormLayout",
        "QGroupBox",
        "QHBoxLayout",
        "QLabel",
        "QMenu",
        "QMessageBox",
        "QPlainTextEdit",
        "QPushButton",
        "QVBoxLayout",
    ]:
        setattr(qt, name, _Dummy)
    qt.QAction = _Action
    qt.QColor = _QColor

    sys.modules["aqt"] = aqt
    sys.modules["aqt.gui_hooks"] = gui_hooks
    sys.modules["aqt.qt"] = qt
    return aqt


def _load_addon():
    _install_aqt_stubs()
    for name in ["bible_verse_displayer", "bible_verse_displayer.config"]:
        sys.modules.pop(name, None)

    spec = importlib.util.spec_from_file_location(
        "bible_verse_displayer",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["bible_verse_displayer"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class UiRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = _load_addon()

    def test_quote_card_has_responsive_high_quality_styles(self):
        html = self.addon._build_quote_html(
            "A long encouraging verse <br>- Test 1:1 (NLT)",
            "#1F2937",
            "Arial, sans-serif",
            "24px",
            "rgba(17, 24, 39, 0.08)",
        )

        self.assertIn('class="bible-verse-displayer"', html)
        self.assertIn("max-width:min(920px, calc(100% - 24px));", html)
        self.assertIn("line-height:1.45;", html)
        self.assertIn("overflow-wrap:anywhere;", html)
        self.assertIn("background-color:rgba(17, 24, 39, 0.08);", html)
        self.assertEqual(html.count("bible-verse-displayer"), 1)

    def test_theme_aware_colors_cover_light_and_dark_modes(self):
        self.addon.mw.theme_manager.night_mode = False
        self.assertEqual(
            self.addon._get_quote_colors(True),
            (self.addon.LIGHT_THEME_QUOTE_COLOR, self.addon.LIGHT_THEME_QUOTE_BACKGROUND),
        )

        self.addon.mw.theme_manager.night_mode = True
        self.assertEqual(
            self.addon._get_quote_colors(True),
            (self.addon.DARK_THEME_QUOTE_COLOR, self.addon.DARK_THEME_QUOTE_BACKGROUND),
        )

    def test_color_validation_rejects_invalid_rgb_channels(self):
        self.assertEqual(self.addon._validate_font_color("rgb(999,999,999)"), "#1E90FF")
        self.assertEqual(self.addon._validate_font_color("rgba(30,144,255,0.7)"), "rgba(30,144,255,0.7)")

    def test_config_has_expected_nlt_entry_counts(self):
        data = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        quotes = data["quote"]
        quoted_verses = set()
        for quote in quotes:
            match = re.search(r"<br>-\s*(.+?)\s+\(NLT\)$", quote)
            self.assertIsNotNone(match, quote)
            ref = match.group(1).replace("–", "-")
            ref_match = re.match(r"(.+?) (\d+):(\d+)(?:-(\d+))?$", ref)
            self.assertIsNotNone(ref_match, ref)
            book = ref_match.group(1)
            chapter = int(ref_match.group(2))
            first = int(ref_match.group(3))
            last = int(ref_match.group(4) or first)
            for verse in range(first, last + 1):
                quoted_verses.add((book, chapter, verse))

        self.assertEqual(len(quotes), 483)
        self.assertEqual(len(quoted_verses), 500)
        self.assertEqual(data["default translation"], "NLT")
        self.assertEqual(data["default entry count"], 483)
        self.assertEqual(data["scripture quoted verse count"], 500)


if __name__ == "__main__":
    unittest.main()
