"""Shared pytest fixtures and configuration for the test suite."""

import pytest

try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except ImportError:
    QApplication = None
    HAS_QT = False


@pytest.fixture(scope="session")
def app():
    """Shared Qt application fixture for all tests requiring Qt.

    This fixture ensures only one QApplication instance exists per test session,
    preventing Qt singleton errors when running multiple test modules.
    """
    if not HAS_QT:
        pytest.skip("Qt not available - skipping Qt-dependent tests")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Note: QApplication cleanup is handled automatically by pytest-qt
