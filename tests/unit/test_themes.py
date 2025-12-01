"""Unit tests for themes.py module."""

import os
from unittest.mock import Mock, patch

import pytest

# Skip all tests in this module if PySide6 is not available
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from transmission_qt_remote import themes


class TestThemes:
    """Test cases for theme utilities."""

    def test_create_palette_from_tokens_light_theme(self):
        """Test palette creation with light theme tokens."""
        palette = themes.create_palette_from_tokens(themes.LIGHT_THEME_TOKENS)

        assert isinstance(palette, QPalette)
        assert palette.color(QPalette.Window) == QColor(
            themes.LIGHT_THEME_TOKENS["background"]
        )
        assert palette.color(QPalette.WindowText) == QColor(
            themes.LIGHT_THEME_TOKENS["foreground"]
        )
        assert palette.color(QPalette.Base) == QColor(
            themes.LIGHT_THEME_TOKENS["surface"]
        )
        assert palette.color(QPalette.Highlight) == QColor(
            themes.LIGHT_THEME_TOKENS["highlight"]
        )

    def test_create_palette_from_tokens_dark_theme(self):
        """Test palette creation with dark theme tokens."""
        palette = themes.create_palette_from_tokens(themes.DARK_THEME_TOKENS)

        assert isinstance(palette, QPalette)
        assert palette.color(QPalette.Window) == QColor(
            themes.DARK_THEME_TOKENS["background"]
        )
        assert palette.color(QPalette.WindowText) == QColor(
            themes.DARK_THEME_TOKENS["foreground"]
        )
        assert palette.color(QPalette.Base) == QColor(
            themes.DARK_THEME_TOKENS["surface"]
        )

    @patch("transmission_qt_remote.themes.qdarkstyle")
    def test_load_muted_dark_stylesheet_with_qdarkstyle(self, mock_qdarkstyle):
        """Test loading muted dark stylesheet when qdarkstyle is available."""
        mock_qdarkstyle.load_stylesheet_pyside6.return_value = (
            "#0277bd { color: #0277bd; } #0091ea { background: #0091ea; }"
        )

        result = themes.load_muted_dark_stylesheet()

        assert themes.MUTED_DARK_ACCENT in result
        assert "#0277bd" not in result  # Should be replaced
        assert "#0091ea" not in result  # Should be replaced
        mock_qdarkstyle.load_stylesheet_pyside6.assert_called_once()

    def test_load_muted_dark_stylesheet_without_qdarkstyle(self):
        """Test loading muted dark stylesheet when qdarkstyle is not available."""
        # Temporarily set qdarkstyle to None
        original_qdarkstyle = themes.qdarkstyle
        themes.qdarkstyle = None

        try:
            result = themes.load_muted_dark_stylesheet()
            assert result == ""
        finally:
            themes.qdarkstyle = original_qdarkstyle

    def test_is_system_dark_mode_env_vars(self):
        """Test system dark mode detection via environment variables."""
        with patch.dict(os.environ, {"QT_QPA_PLATFORMTHEME": "dark"}):
            assert themes.is_system_dark_mode() is True

        with patch.dict(os.environ, {"COLORSCHEME": "dark"}):
            assert themes.is_system_dark_mode() is True

        # Test with no dark mode environment variables
        # Note: Qt might still detect dark mode, so we just test that it doesn't crash
        with patch.dict(
            os.environ, {"QT_QPA_PLATFORMTHEME": "light", "COLORSCHEME": "light"}
        ):
            result = themes.is_system_dark_mode()
            assert isinstance(result, bool)  # Should return a boolean without crashing

    @patch("transmission_qt_remote.themes.QApplication.instance")
    def test_is_system_dark_mode_qt_hints(self, mock_app_instance):
        """Test system dark mode detection via Qt style hints."""
        mock_app = Mock()
        mock_hints = Mock()
        mock_hints.colorScheme.return_value = Qt.ColorScheme.Dark
        mock_app.styleHints.return_value = mock_hints
        mock_app_instance.return_value = mock_app

        assert themes.is_system_dark_mode() is True

    @patch("transmission_qt_remote.themes.QApplication.instance")
    def test_is_system_dark_mode_palette_luminance(self, mock_app_instance):
        """Test system dark mode detection via palette luminance."""
        mock_app = Mock()
        mock_hints = Mock()
        mock_hints.colorScheme.return_value = Qt.ColorScheme.Light
        mock_app.styleHints.return_value = mock_hints

        # Mock palette with dark window color (low luminance)
        mock_palette = Mock()
        mock_color = Mock()
        mock_color.red.return_value = 50
        mock_color.green.return_value = 50
        mock_color.blue.return_value = 50
        mock_palette.color.return_value = mock_color
        mock_app.palette.return_value = mock_palette
        mock_app_instance.return_value = mock_app

        assert themes.is_system_dark_mode() is True

    @patch("transmission_qt_remote.themes.QApplication.instance")
    def test_is_system_dark_mode_no_app(self, mock_app_instance):
        """Test system dark mode detection when no QApplication exists."""
        mock_app_instance.return_value = None
        assert themes.is_system_dark_mode() is False

    def test_apply_palette_to_app(self):
        """Test applying palette to application."""
        mock_app = Mock()
        tokens = themes.LIGHT_THEME_TOKENS

        themes.apply_palette_to_app(mock_app, tokens)

        # Verify that setPalette was called
        mock_app.setPalette.assert_called_once()
        palette_arg = mock_app.setPalette.call_args[0][0]
        assert isinstance(palette_arg, QPalette)

    def test_apply_system_palette(self):
        """Test applying system palette to application."""
        mock_app = Mock()
        mock_style = Mock()
        mock_palette = Mock()
        mock_style.standardPalette.return_value = mock_palette
        mock_app.style.return_value = mock_style

        themes.apply_system_palette(mock_app)

        mock_app.setStyleSheet.assert_called_once_with("")
        mock_app.setPalette.assert_called_once_with(mock_palette)
