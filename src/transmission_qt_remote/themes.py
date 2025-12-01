"""
Theme utilities for TransmissionQtRemote.
"""

import os
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

try:
    import qdarkstyle
except ImportError:
    qdarkstyle = None

LIGHT_THEME_TOKENS = {
    "background": "#ffffff",
    "foreground": "#000000",
    "surface": "#f5f5f5",
    "accent": "#007acc",
    "onAccent": "#ffffff",
    "error": "#d32f2f",
    "onError": "#ffffff",
    "discreteText": "#666666",
    "border": "#e0e0e0",
    "highlight": "#e3f2fd",
}

DARK_THEME_TOKENS = {
    "background": "#121212",
    "foreground": "#ffffff",
    "surface": "#1e1e1e",
    "accent": "#4fc3f7",
    "onAccent": "#000000",
    "error": "#ef5350",
    "onError": "#000000",
    "discreteText": "#b0b0b0",
    "border": "#333333",
    "highlight": "#1565c0",
}

MUTED_DARK_ACCENT = "#424242"
_DARK_ACCENT_OVERRIDES = ["#0277bd", "#0091ea", "#80d8ff"]


def create_palette_from_tokens(tokens: Dict[str, str]) -> QPalette:
    """Build a QPalette populated with the provided color tokens."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(tokens["background"]))
    palette.setColor(QPalette.WindowText, QColor(tokens["foreground"]))
    palette.setColor(QPalette.Base, QColor(tokens["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(tokens["highlight"]))
    palette.setColor(QPalette.Text, QColor(tokens["foreground"]))
    palette.setColor(QPalette.Button, QColor(tokens["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(tokens["foreground"]))
    palette.setColor(QPalette.Highlight, QColor(tokens["highlight"]))
    palette.setColor(QPalette.HighlightedText, QColor(tokens["onAccent"]))
    palette.setColor(QPalette.ToolTipBase, QColor(tokens["surface"]))
    palette.setColor(QPalette.ToolTipText, QColor(tokens["foreground"]))
    palette.setColor(QPalette.Link, QColor(tokens["accent"]))
    palette.setColor(QPalette.PlaceholderText, QColor(tokens["discreteText"]))
    return palette


def apply_palette_to_app(app: QApplication, tokens: Dict[str, str]) -> None:
    """Apply the provided token-based palette to the application."""
    palette = create_palette_from_tokens(tokens)
    app.setPalette(palette)


def load_muted_dark_stylesheet() -> str:
    """Load qdarkstyle and replace bright blue accents with muted gray."""
    if qdarkstyle is None:
        return ""

    stylesheet = qdarkstyle.load_stylesheet_pyside6()
    for accent in _DARK_ACCENT_OVERRIDES:
        stylesheet = stylesheet.replace(accent, MUTED_DARK_ACCENT)
        stylesheet = stylesheet.replace(accent.upper(), MUTED_DARK_ACCENT)
    return stylesheet


def is_system_dark_mode() -> bool:
    """Detect if the operating system prefers a dark palette."""
    platform_theme = os.environ.get("QT_QPA_PLATFORMTHEME", "").lower()
    colorscheme = os.getenv("COLORSCHEME", "light").lower()
    if platform_theme == "dark" or colorscheme == "dark":
        return True

    app = QApplication.instance()
    if not app:
        return False

    hints = app.styleHints()
    if hints.colorScheme() == Qt.ColorScheme.Dark:
        return True

    palette = app.palette()
    window_color = palette.color(QPalette.Window)
    luminance = (
        0.299 * window_color.red()
        + 0.587 * window_color.green()
        + 0.114 * window_color.blue()
    )
    return luminance < 128


def apply_system_palette(app: QApplication) -> None:
    """Restore the native palette so macOS colors remain intact."""
    app.setStyleSheet("")
    app.setPalette(app.style().standardPalette())
