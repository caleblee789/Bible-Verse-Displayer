"""
Bible Verse Displayer add-on for Anki.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import random
import re
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from aqt import mw
from aqt.gui_hooks import deck_browser_will_render_content
from aqt.qt import (
    QAction,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QColor,
    QPushButton,
    QVBoxLayout,
)

from .config import gc

DEFAULT_FONT_COLOR = "#1E90FF"
DEFAULT_FONT_FAMILY = "Arial, sans-serif"
DEFAULT_FONT_SIZE = "24px"
LIGHT_THEME_QUOTE_COLOR = "#1F2937"
LIGHT_THEME_QUOTE_BACKGROUND = "rgba(17, 24, 39, 0.08)"
DARK_THEME_QUOTE_COLOR = "#E6EDF3"
DARK_THEME_QUOTE_BACKGROUND = "rgba(255, 255, 255, 0.12)"
QUOTE_CONTAINER_STYLE = (
    "box-sizing:border-box; width:100%; margin:12px auto 4px;"
    " padding:0 12px; text-align:center;"
)
QUOTE_CARD_BASE_STYLE = (
    "box-sizing:border-box; display:inline-block;"
    " max-width:min(920px, calc(100% - 24px));"
    " line-height:1.45; text-align:center; white-space:normal;"
    " overflow-wrap:anywhere; word-break:normal;"
    " border-radius:8px; padding:8px 12px;"
)

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
RGB_COLOR_RE = re.compile(
    r"^rgba?\(\s*(?:\d{1,3}\s*,\s*){2}\d{1,3}(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$"
)
NAMED_COLOR_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]{0,31}$")
SIZE_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>px|em|rem|%)$")


def _validate_font_color(value: object, default: str = DEFAULT_FONT_COLOR) -> str:
    if not isinstance(value, str):
        return default

    candidate = value.strip()
    if not candidate:
        return default

    if HEX_COLOR_RE.fullmatch(candidate):
        return candidate

    if RGB_COLOR_RE.fullmatch(candidate) and QColor.isValidColor(candidate):
        return candidate

    if NAMED_COLOR_RE.fullmatch(candidate) and QColor.isValidColor(candidate):
        return candidate

    # Conservative parser fallback for uncommon, but valid color formats.
    if QColor.isValidColor(candidate):
        return candidate

    return default


def _validate_font_size(value: object, default: str = DEFAULT_FONT_SIZE) -> str:
    if not isinstance(value, str):
        return default

    candidate = value.strip().lower()
    match = SIZE_RE.fullmatch(candidate)
    if not match:
        return default

    numeric_value = float(match.group("value"))
    unit = match.group("unit")

    limits = {
        "px": (8, 96),
        "em": (0.5, 6),
        "rem": (0.5, 6),
        "%": (50, 300),
    }
    lower, upper = limits[unit]
    if lower <= numeric_value <= upper:
        return candidate

    return default


def _validate_font_family(value: object, default: str = DEFAULT_FONT_FAMILY) -> str:
    if not isinstance(value, str):
        return default

    candidate = value.strip()
    if not candidate:
        return default

    if any(char in candidate for char in ";<>\"'"):
        return default

    return candidate


last_quote: str = ""
last_refresh_key: str = ""


def _get_rotation_mode() -> str:
    mode = gc("rotation mode", "daily")
    if not isinstance(mode, str):
        return "daily"

    normalized = mode.strip().lower()
    if normalized in {"every render", "daily", "manual"}:
        return normalized
    return "daily"


def _get_refresh_key() -> str:
    mode = _get_rotation_mode()
    if mode == "every render":
        return f"every-render:{datetime.now(timezone.utc).isoformat(timespec='microseconds')}"
    if mode == "daily":
        return f"daily:{datetime.now(timezone.utc).date().isoformat()}"
    return "manual"


def _get_cached_quote() -> str:
    global last_quote, last_refresh_key

    refresh_key = _get_refresh_key()
    if last_quote and refresh_key == last_refresh_key:
        return last_quote

    quote = _get_random_quote()
    if not quote:
        return ""

    last_quote = quote
    last_refresh_key = refresh_key
    return quote


def _clear_quote_cache() -> None:
    global last_quote, last_refresh_key
    last_quote = ""
    last_refresh_key = ""


def _get_random_quote() -> str:
    quotes = gc("quote", default=[])
    if not isinstance(quotes, list):
        return ""

    valid_quotes = [q for q in quotes if isinstance(q, str) and q.strip()]
    if not valid_quotes:
        return ""

    return random.choice(valid_quotes)


def add_new_count_to_bottom(_dbinstance, content):
    quote = _get_cached_quote()
    if not quote:
        return

    family = _validate_font_family(gc("font family", DEFAULT_FONT_FAMILY))
    size = _validate_font_size(gc("font size", DEFAULT_FONT_SIZE))
    use_theme_aware_color = gc("use theme-aware color", True)
    color, background_color = _get_quote_colors(use_theme_aware_color)
    content.stats += _build_quote_html(quote, color, family, size, background_color)


def _get_quote_colors(use_theme_aware_color: bool) -> Tuple[str, Optional[str]]:
    if not use_theme_aware_color:
        return _validate_font_color(gc("font color", DEFAULT_FONT_COLOR)), None

    if _is_dark_theme():
        return DARK_THEME_QUOTE_COLOR, DARK_THEME_QUOTE_BACKGROUND
    return LIGHT_THEME_QUOTE_COLOR, LIGHT_THEME_QUOTE_BACKGROUND


def _build_quote_html(
    quote: str,
    color: str,
    family: str,
    size: str,
    background_color: Optional[str],
) -> str:
    background_style = f" background-color:{background_color};" if background_color else ""
    card_style = (
        f"color:{color}; font-size:{size}; font-family:{family};"
        f"{QUOTE_CARD_BASE_STYLE}{background_style}"
    )
    return (
        f'<div class="bible-verse-displayer" style="{QUOTE_CONTAINER_STYLE}">'
        f'<div style="{card_style}">{quote}</div>'
        "</div>"
    )


def _is_dark_theme() -> bool:
    theme_manager = getattr(mw, "theme_manager", None)
    if theme_manager:
        night_mode = getattr(theme_manager, "night_mode", None)
        if isinstance(night_mode, bool):
            return night_mode
        if callable(night_mode):
            try:
                return bool(night_mode())
            except (TypeError, AttributeError) as exc:
                print(f"Bible Verse Displayer: could not determine theme via night_mode(): {exc}")

    app = getattr(mw, "app", None)
    palette = app.palette() if app and hasattr(app, "palette") else None
    if palette and hasattr(palette, "window"):
        return palette.window().color().lightness() < 128

    return False


def _normalize_quotes(raw_quotes: str) -> List[str]:
    return [line.strip() for line in raw_quotes.splitlines() if line.strip()]


class BibleVerseDisplaySettingsDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bible Verse Display Settings")
        self.resize(760, 640)
        self.setMinimumSize(700, 620)

        self.quotes_edit = QPlainTextEdit(self)
        self.quotes_edit.setPlaceholderText(
            "One verse or message per line. HTML tags like <br> are supported."
        )
        self.quotes_edit.setMinimumHeight(220)
        quotes = gc("quote", default=[])
        if isinstance(quotes, list):
            self.quotes_edit.setPlainText("\n".join([q for q in quotes if isinstance(q, str)]))
        self.quotes_edit.textChanged.connect(self._update_quote_count)
        self.quotes_edit.textChanged.connect(self._update_preview)
        self.quote_count_label = QLabel(self)

        self.color_combo = QComboBox(self)
        self.color_combo.setEditable(True)
        preset_colors = [
            DEFAULT_FONT_COLOR,
            "#FFFFFF",
            "#000000",
            "#FFD700",
            "#32CD32",
            "#FF69B4",
            "#FF4500",
            "#9370DB",
            "#00CED1",
        ]
        self.color_combo.addItems(preset_colors)
        self.color_combo.setCurrentText(gc("font color", DEFAULT_FONT_COLOR))
        self.color_combo.currentTextChanged.connect(self._update_preview)
        self.color_button = QPushButton("Choose...", self)
        self.color_button.clicked.connect(self._choose_color)

        self.theme_aware_color_checkbox = QCheckBox("Use theme-aware color", self)
        self.theme_aware_color_checkbox.setChecked(gc("use theme-aware color", True))
        self.theme_aware_color_checkbox.toggled.connect(self._on_theme_aware_toggled)
        self.theme_aware_color_checkbox.toggled.connect(self._update_preview)

        self.family_combo = QComboBox(self)
        self.family_combo.setEditable(True)
        self.family_combo.addItems(
            [
                DEFAULT_FONT_FAMILY,
                "Times New Roman, serif",
                "Georgia, serif",
            ]
        )
        self.family_combo.setCurrentText(gc("font family", DEFAULT_FONT_FAMILY))
        self.family_combo.currentTextChanged.connect(self._update_preview)

        self.size_combo = QComboBox(self)
        self.size_combo.setEditable(True)
        self.size_combo.addItems(["12px", "16px", "20px", "24px", "28px", "32px"])
        self.size_combo.setCurrentText(gc("font size", DEFAULT_FONT_SIZE))
        self.size_combo.currentTextChanged.connect(self._update_preview)

        self.rotation_mode_combo = QComboBox(self)
        self.rotation_mode_combo.addItems(["daily", "every render", "manual"])
        self.rotation_mode_combo.setCurrentText(_get_rotation_mode())
        self.rotation_mode_combo.setToolTip(
            "Daily keeps one verse per day. Every render changes on redraw. Manual keeps the "
            "current verse until settings change."
        )

        form_layout = QFormLayout()
        growth_policy = (
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
            if hasattr(QFormLayout, "FieldGrowthPolicy")
            else QFormLayout.AllNonFixedFieldsGrow
        )
        form_layout.setFieldGrowthPolicy(growth_policy)
        form_layout.addRow("Color mode:", self.theme_aware_color_checkbox)

        color_layout = QHBoxLayout()
        color_layout.addWidget(self.color_combo, 1)
        color_layout.addWidget(self.color_button)
        form_layout.addRow("Custom color:", color_layout)
        form_layout.addRow("Font family:", self.family_combo)
        form_layout.addRow("Font size:", self.size_combo)

        io_buttons_layout = QHBoxLayout()
        import_button = QPushButton("Import", self)
        import_button.clicked.connect(self._import_quotes)
        export_button = QPushButton("Export", self)
        export_button.clicked.connect(self._export_quotes)
        io_buttons_layout.addWidget(import_button)
        io_buttons_layout.addWidget(export_button)
        io_buttons_layout.addStretch(1)
        io_buttons_layout.addWidget(self.quote_count_label)

        behavior_layout = QFormLayout()
        behavior_layout.addRow("Rotation mode:", self.rotation_mode_combo)

        quotes_group = QGroupBox("Verses", self)
        quotes_layout = QVBoxLayout(quotes_group)
        quotes_help = QLabel("Add one entry per line. Blank lines are ignored.", self)
        quotes_help.setWordWrap(True)
        quotes_layout.addWidget(quotes_help)
        quotes_layout.addWidget(self.quotes_edit, 1)
        quotes_layout.addLayout(io_buttons_layout)

        appearance_group = QGroupBox("Appearance", self)
        appearance_group.setLayout(form_layout)

        behavior_group = QGroupBox("Behavior", self)
        behavior_group.setLayout(behavior_layout)

        self.preview_label = QLabel(self)
        self.preview_label.setWordWrap(True)
        self.preview_label.setMinimumHeight(110)
        self.preview_label.setStyleSheet(
            "QLabel { border: 1px solid palette(mid); border-radius: 8px;"
            " padding: 14px; background: palette(base); }"
        )
        preview_group = QGroupBox("Preview", self)
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self.preview_label)

        buttons = QDialogButtonBox(
            (
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
                if hasattr(QDialogButtonBox, "StandardButton")
                else QDialogButtonBox.Save | QDialogButtonBox.Cancel
            ),
            self,
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        reset_appearance_button = QPushButton("Reset Appearance", self)
        reset_appearance_button.clicked.connect(self._reset_appearance)
        button_row = QHBoxLayout()
        button_row.addWidget(reset_appearance_button)
        button_row.addStretch(1)
        button_row.addWidget(buttons)

        layout = QVBoxLayout(self)
        heading = QLabel("<b>Bible Verse Display Settings</b>", self)
        heading.setToolTip("Configure the verse shown at the bottom of Anki's deck browser.")
        layout.addWidget(heading)
        layout.addWidget(quotes_group, 1)
        layout.addWidget(appearance_group)
        layout.addWidget(behavior_group)
        layout.addWidget(preview_group)
        layout.addLayout(button_row)
        self._on_theme_aware_toggled(self.theme_aware_color_checkbox.isChecked())
        self._update_quote_count()
        self._update_preview()

    def _on_theme_aware_toggled(self, enabled: bool) -> None:
        self.color_combo.setEnabled(not enabled)
        self.color_button.setEnabled(not enabled)
        tooltip = (
            "Theme-aware mode automatically chooses readable quote colors for light/dark themes."
            if enabled
            else "Choose a custom text color for the quote."
        )
        self.color_combo.setToolTip(tooltip)
        self.color_button.setToolTip(tooltip)

    def _choose_color(self) -> None:
        current_color = QColor(_validate_font_color(self.color_combo.currentText()))
        selected_color = QColorDialog.getColor(current_color, self, "Choose Quote Color")
        if selected_color.isValid():
            self.color_combo.setCurrentText(selected_color.name())

    def _reset_appearance(self) -> None:
        self.theme_aware_color_checkbox.setChecked(True)
        self.color_combo.setCurrentText(DEFAULT_FONT_COLOR)
        self.family_combo.setCurrentText(DEFAULT_FONT_FAMILY)
        self.size_combo.setCurrentText(DEFAULT_FONT_SIZE)
        self._update_preview()

    def _update_quote_count(self) -> None:
        count = len(_normalize_quotes(self.quotes_edit.toPlainText()))
        label = "entry" if count == 1 else "entries"
        self.quote_count_label.setText(f"{count} {label}")

    def _preview_quote(self) -> str:
        quotes = _normalize_quotes(self.quotes_edit.toPlainText())
        if quotes:
            return quotes[0]
        return "Your preview will appear here after you add a verse."

    def _update_preview(self) -> None:
        use_theme_aware_color = self.theme_aware_color_checkbox.isChecked()
        if use_theme_aware_color:
            color, background_color = _get_quote_colors(True)
        else:
            color = _validate_font_color(self.color_combo.currentText(), DEFAULT_FONT_COLOR)
            background_color = None

        family = _validate_font_family(self.family_combo.currentText(), DEFAULT_FONT_FAMILY)
        size = _validate_font_size(self.size_combo.currentText(), DEFAULT_FONT_SIZE)
        self.preview_label.setText(
            _build_quote_html(self._preview_quote(), color, family, size, background_color)
        )

    def _import_quotes(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Verses",
            "",
            "Supported Files (*.txt *.json);;Text Files (*.txt);;JSON Files (*.json)",
        )
        if not file_path:
            return

        try:
            with open(file_path, encoding="utf-8") as import_file:
                raw_contents = import_file.read()
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Import Failed",
                f"Unable to read file:\n{exc}",
            )
            return

        try:
            if file_path.lower().endswith(".json"):
                parsed = json.loads(raw_contents)
                if not isinstance(parsed, list):
                    raise ValueError("JSON root must be a list.")
                if not all(isinstance(item, str) for item in parsed):
                    raise ValueError("JSON list must contain only strings.")
                normalized_quotes = _normalize_quotes("\n".join(parsed))
            else:
                normalized_quotes = _normalize_quotes(raw_contents)
        except (json.JSONDecodeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Import Failed",
                f"Malformed import file:\n{exc}",
            )
            return

        if not normalized_quotes:
            QMessageBox.warning(
                self,
                "Import Failed",
                "No valid verses/messages were found in the selected file.",
            )
            return

        self.quotes_edit.setPlainText("\n".join(normalized_quotes))

    def _export_quotes(self) -> None:
        quotes = _normalize_quotes(self.quotes_edit.toPlainText())
        if not quotes:
            QMessageBox.warning(
                self,
                "Export Failed",
                "There are no verses/messages to export.",
            )
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Verses",
            "",
            "Text Files (*.txt);;JSON Files (*.json)",
        )
        if not file_path:
            return

        export_as_json = "JSON" in selected_filter or file_path.lower().endswith(".json")

        if export_as_json and not file_path.lower().endswith(".json"):
            file_path = f"{file_path}.json"
        elif not export_as_json and not file_path.lower().endswith(".txt"):
            file_path = f"{file_path}.txt"

        try:
            with open(file_path, "w", encoding="utf-8") as export_file:
                if export_as_json:
                    json.dump(quotes, export_file, ensure_ascii=False, indent=2)
                    export_file.write("\n")
                else:
                    export_file.write("\n".join(quotes))
                    export_file.write("\n")
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Unable to write file:\n{exc}",
            )

    def _save(self) -> None:
        quotes = _normalize_quotes(self.quotes_edit.toPlainText())
        if not quotes:
            QMessageBox.warning(
                self,
                "Bible Verse Display Settings",
                "Please add at least one verse/message entry before saving.",
            )
            return

        use_theme_aware_color = self.theme_aware_color_checkbox.isChecked()
        raw_color = self.color_combo.currentText().strip()
        raw_family = self.family_combo.currentText().strip()
        raw_size = self.size_combo.currentText().strip()
        font_color = _validate_font_color(raw_color, DEFAULT_FONT_COLOR)
        font_family = _validate_font_family(raw_family, DEFAULT_FONT_FAMILY)
        font_size = _validate_font_size(raw_size, DEFAULT_FONT_SIZE)

        if not use_theme_aware_color and font_color == DEFAULT_FONT_COLOR and raw_color != DEFAULT_FONT_COLOR:
            QMessageBox.warning(
                self,
                "Bible Verse Display Settings",
                "Please enter a valid custom color, such as #1E90FF, rgb(30,144,255), or dodgerblue.",
            )
            return

        if font_family == DEFAULT_FONT_FAMILY and raw_family != DEFAULT_FONT_FAMILY:
            QMessageBox.warning(
                self,
                "Bible Verse Display Settings",
                "Please enter a font family without quotes, semicolons, or angle brackets.",
            )
            return

        if font_size == DEFAULT_FONT_SIZE and raw_size.lower() != DEFAULT_FONT_SIZE:
            QMessageBox.warning(
                self,
                "Bible Verse Display Settings",
                "Please enter a font size with a valid unit, such as 16px, 1.2em, or 120%.",
            )
            return

        config = mw.addonManager.getConfig(__name__) or {}
        config["quote"] = quotes
        config["font color"] = font_color
        config["font family"] = font_family
        config["font size"] = font_size
        config["use theme-aware color"] = use_theme_aware_color
        config["rotation mode"] = self.rotation_mode_combo.currentText().strip() or "daily"
        mw.addonManager.writeConfig(__name__, config)
        _clear_quote_cache()
        self.accept()


def open_settings_dialog():
    dialog = BibleVerseDisplaySettingsDialog(mw)
    if dialog.exec():
        mw.moveToState("deckBrowser")


def add_settings_menu():
    tools_menu = mw.form.menuTools
    settings_menu = QMenu("Bible Verse Display Settings", mw)
    open_settings_action = QAction("Open Bible Verse Display Settings", mw)
    open_settings_action.triggered.connect(open_settings_dialog)
    settings_menu.addAction(open_settings_action)
    tools_menu.addMenu(settings_menu)


deck_browser_will_render_content.append(add_new_count_to_bottom)
add_settings_menu()


# reset background when changing config
def apply_config_changes(_config):
    _clear_quote_cache()
    mw.moveToState("deckBrowser")


mw.addonManager.setConfigUpdatedAction(__name__, apply_config_changes)
