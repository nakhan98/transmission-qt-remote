"""Integration tests for torrent menu functionality."""

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from transmission_qt_remote.main_window import TransmissionClient


@pytest.fixture
def app():
    """Create QApplication for testing."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    return app


def test_torrent_menu_exists(app):
    """Test that Torrent menu exists in menu bar."""
    client = TransmissionClient()

    # Get menu bar
    menubar = client.menuBar()

    # Find Torrent menu
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    assert torrent_menu_action is not None, "Torrent menu not found in menu bar"

    # Check menu has expected actions
    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # Should have: Start, Force Start, Pause, separator, Verify, separator, Delete, Delete with Data
    assert len(actions) == 8, f"Expected 8 actions, got {len(actions)}"

    # Check action texts (separators return empty string)
    expected_texts = [
        "&Start",
        "Force &Start",
        "&Pause",
        "",
        "&Verify",
        "",
        "&Delete",
        "Delete with &Data",
    ]
    actual_texts = [action.text() if action else "" for action in actions]
    assert actual_texts == expected_texts, (
        f"Expected {expected_texts}, got {actual_texts}"
    )


def test_torrent_menu_initially_disabled(app):
    """Test that torrent menu actions are initially disabled."""
    client = TransmissionClient()

    # Get torrent menu actions
    menubar = client.menuBar()
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # Check that main actions are initially disabled
    assert not actions[0].isEnabled(), "Start action should be initially disabled"
    assert not actions[1].isEnabled(), "Force Start action should be initially disabled"
    assert not actions[2].isEnabled(), "Pause action should be initially disabled"
    assert not actions[4].isEnabled(), "Verify action should be initially disabled"

    # Delete actions should always be disabled (read-only client)
    assert not actions[6].isEnabled(), "Delete action should be disabled (read-only)"
    assert not actions[7].isEnabled(), (
        "Delete with Data action should be disabled (read-only)"
    )


def test_torrent_menu_actions_enable_with_selection(app):
    """Test that torrent menu actions are enabled when torrent is selected."""
    client = TransmissionClient()

    # Mock torrent data
    mock_torrent = {
        "id": 1,
        "name": "Test Torrent",
        "status": 0,  # Stopped
        "sizeWhenDone": 1000000,
        "leftUntilDone": 1000000,
        "rateDownload": 0,
        "rateUpload": 0,
        "eta": -1,
        "uploadedEver": 0,
        "downloadedEver": 0,
        "ratio": 0.0,
        "peersConnected": 0,
        "peersGettingFromUs": 0,
        "peersSendingToUs": 0,
        "webseedsSendingToUs": 0,
        "error": 0,
        "errorString": "",
        "doneDate": 0,
        "haveValid": 0,
        "haveUnchecked": 0,
        "addedDate": 1234567890,
        "trackers": [],
        "files": [],
        "priorities": [],
        "wanted": [],
    }

    client.displayed_torrents = [mock_torrent]
    client.table.setRowCount(1)

    # Create a mock item for the table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)

    # Manually trigger selection change by emitting the signal
    client.table.itemSelectionChanged.emit()

    # Process events to ensure signal is handled
    QTest.qWait(100)

    # Manually call selection handler to ensure it runs
    client._on_table_selection_changed()

    # Debug: check if torrent menu actions exist
    assert hasattr(client, "torrent_start_action"), "torrent_start_action should exist"

    # Get torrent menu actions
    menubar = client.menuBar()
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # For stopped torrent, Start and Force Start should be enabled
    assert actions[0].isEnabled(), "Start action should be enabled for stopped torrent"
    assert actions[1].isEnabled(), (
        "Force Start action should be enabled for stopped torrent"
    )
    assert not actions[2].isEnabled(), (
        "Pause action should be disabled for stopped torrent"
    )
    assert actions[4].isEnabled(), "Verify action should be enabled"


def test_torrent_menu_actions_for_active_torrent(app):
    """Test that torrent menu actions are correctly enabled for active torrents."""
    client = TransmissionClient()

    # Mock active torrent data
    mock_torrent = {
        "id": 1,
        "name": "Test Torrent",
        "status": 6,  # Seeding (active)
        "sizeWhenDone": 1000000,
        "leftUntilDone": 500000,
        "rateDownload": 1000,
        "rateUpload": 0,
        "eta": 500,
        "uploadedEver": 0,
        "downloadedEver": 500000,
        "ratio": 0.0,
        "peersConnected": 5,
        "peersGettingFromUs": 0,
        "peersSendingToUs": 3,
        "webseedsSendingToUs": 0,
        "error": 0,
        "errorString": "",
        "doneDate": 0,
        "haveValid": 500000,
        "haveUnchecked": 0,
        "addedDate": 1234567890,
        "trackers": [],
        "files": [],
        "priorities": [],
        "wanted": [],
    }

    client.displayed_torrents = [mock_torrent]
    client.table.setRowCount(1)

    # Create a mock item for the table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)

    # Manually trigger selection change by emitting the signal
    client.table.itemSelectionChanged.emit()

    # Process events to ensure signal is handled
    QTest.qWait(100)

    # Manually call selection handler to ensure it runs
    client._on_table_selection_changed()

    # Get torrent menu actions
    menubar = client.menuBar()
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # For active torrent, Pause should be enabled, Start/Force Start disabled
    assert not actions[0].isEnabled(), (
        "Start action should be disabled for active torrent"
    )
    assert not actions[1].isEnabled(), (
        "Force Start action should be disabled for active torrent"
    )
    assert actions[2].isEnabled(), "Pause action should be enabled for active torrent"
    assert actions[4].isEnabled(), "Verify action should be enabled"


def test_torrent_menu_keyboard_shortcuts(app):
    """Test that torrent menu actions have correct keyboard shortcuts."""
    client = TransmissionClient()

    # Get torrent menu actions
    menubar = client.menuBar()
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # Check shortcuts
    assert actions[0].shortcut() == QKeySequence("Ctrl+S"), (
        "Start action should have Ctrl+S shortcut"
    )
    assert actions[1].shortcut() == QKeySequence("Ctrl+Shift+S"), (
        "Force Start action should have Ctrl+Shift+S shortcut"
    )
    assert actions[2].shortcut() == QKeySequence("Ctrl+P"), (
        "Pause action should have Ctrl+P shortcut"
    )
    assert actions[4].shortcut() == QKeySequence("Ctrl+R"), (
        "Verify action should have Ctrl+R shortcut"
    )


def test_torrent_menu_actions_trigger_methods(app):
    """Test that torrent menu actions trigger the correct methods."""
    client = TransmissionClient()

    # Mock torrent data
    mock_torrent = {
        "id": 1,
        "name": "Test Torrent",
        "status": 0,  # Stopped
        "sizeWhenDone": 1000000,
        "leftUntilDone": 1000000,
        "rateDownload": 0,
        "rateUpload": 0,
        "eta": -1,
        "uploadedEver": 0,
        "downloadedEver": 0,
        "ratio": 0.0,
        "peersConnected": 0,
        "peersGettingFromUs": 0,
        "peersSendingToUs": 0,
        "webseedsSendingToUs": 0,
        "error": 0,
        "errorString": "",
        "doneDate": 0,
        "haveValid": 0,
        "haveUnchecked": 0,
        "addedDate": 1234567890,
        "trackers": [],
        "files": [],
        "priorities": [],
        "wanted": [],
    }

    client.displayed_torrents = [mock_torrent]
    client.table.setRowCount(1)

    # Create a mock item for the table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)

    # Manually trigger selection change by emitting the signal
    client.table.itemSelectionChanged.emit()

    # Process events to ensure signal is handled
    QTest.qWait(100)

    # Manually call selection handler to ensure it runs
    client._on_table_selection_changed()

    # Get torrent menu actions
    menubar = client.menuBar()
    torrent_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Torrent":
            torrent_menu_action = action
            break

    torrent_menu = torrent_menu_action.menu()
    actions = torrent_menu.actions()

    # Mock the start_torrent method to track calls
    original_start = client.start_torrent
    start_called = False
    start_torrent_id = None

    def mock_start_torrent(torrent_id):
        nonlocal start_called, start_torrent_id
        start_called = True
        start_torrent_id = torrent_id

    client.start_torrent = mock_start_torrent

    # Trigger Start action
    actions[0].trigger()

    # Verify method was called with correct torrent ID
    assert start_called, "start_torrent method should be called"
    assert start_torrent_id == 1, (
        "start_torrent should be called with correct torrent ID"
    )

    # Restore original method
    client.start_torrent = original_start
