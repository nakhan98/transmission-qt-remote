"""Integration tests for torrent toolbar functionality."""

import pytest
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


def test_torrent_toolbar_exists(app):
    """Test that torrent toolbar exists in main window."""
    client = TransmissionClient()

    # Check that toolbar exists
    assert hasattr(client, "torrent_toolbar"), "Torrent toolbar should exist"
    assert client.torrent_toolbar.windowTitle() == "Torrent Actions"


def test_torrent_toolbar_actions_count(app):
    """Test that toolbar has correct number of actions."""
    client = TransmissionClient()

    # Check action count (Open, separator, Start, Force Start, Pause, separator, Delete)
    actions = client.torrent_toolbar.actions()
    assert len(actions) == 7, (
        f"Expected 7 actions (including separators), got {len(actions)}"
    )


def test_torrent_toolbar_action_names(app):
    """Test that toolbar has correct action names."""
    client = TransmissionClient()

    actions = client.torrent_toolbar.actions()
    action_names = [action.text() for action in actions]

    # Include separators (empty text) in expected names
    expected_names = ["Open", "", "Start", "Force Start", "Pause", "", "Delete"]
    assert action_names == expected_names, (
        f"Expected {expected_names}, got {action_names}"
    )


def test_torrent_toolbar_initially_disabled(app):
    """Test that toolbar actions are initially disabled."""
    client = TransmissionClient()

    actions = client.torrent_toolbar.actions()

    # Named actions should be initially disabled, separators are enabled
    for action in actions:
        if action.text():  # Skip separators (empty text)
            assert not action.isEnabled(), (
                f"Action '{action.text()}' should be initially disabled"
            )


def test_torrent_toolbar_enable_with_selection(app):
    """Test that toolbar actions are enabled when torrent is selected."""
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

    # Create a mock item for table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)

    # Manually trigger selection change
    client._on_table_selection_changed()

    # Check toolbar actions
    actions = client.torrent_toolbar.actions()

    # For stopped torrent, Start and Force Start should be enabled
    # Actions: [0] Open, [1] separator, [2] Start, [3] Force Start, [4] Pause, [5] separator, [6] Delete
    assert actions[2].isEnabled(), "Start action should be enabled for stopped torrent"
    assert actions[3].isEnabled(), (
        "Force Start action should be enabled for stopped torrent"
    )
    assert not actions[4].isEnabled(), (
        "Pause action should be disabled for stopped torrent"
    )


def test_torrent_toolbar_for_active_torrent(app):
    """Test that toolbar actions are correctly enabled for active torrents."""
    client = TransmissionClient()

    # Mock active torrent data
    mock_torrent = {
        "id": 1,
        "name": "Test Torrent",
        "status": 6,  # Seeding (active)
        "sizeWhenDone": 1000000,
        "leftUntilDone": 0,
        "rateDownload": 0,
        "rateUpload": 1000,
        "eta": -1,
        "uploadedEver": 2000000,
        "downloadedEver": 1000000,
        "ratio": 2.0,
        "peersConnected": 5,
        "peersGettingFromUs": 3,
        "peersSendingToUs": 0,
        "webseedsSendingToUs": 0,
        "error": 0,
        "errorString": "",
        "doneDate": 1234567890,
        "haveValid": 1000000,
        "haveUnchecked": 0,
        "addedDate": 1234567890,
        "trackers": [],
        "files": [],
        "priorities": [],
        "wanted": [],
    }

    client.displayed_torrents = [mock_torrent]
    client.table.setRowCount(1)

    # Create a mock item for table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)

    # Manually trigger selection change
    client._on_table_selection_changed()

    # Check toolbar actions
    actions = client.torrent_toolbar.actions()

    # For active torrent, Pause should be enabled, Start/Force Start disabled
    # Actions: [0] Open, [1] separator, [2] Start, [3] Force Start, [4] Pause, [5] separator, [6] Delete
    assert not actions[2].isEnabled(), (
        "Start action should be disabled for active torrent"
    )
    assert not actions[3].isEnabled(), (
        "Force Start action should be disabled for active torrent"
    )
    assert actions[4].isEnabled(), "Pause action should be enabled for active torrent"


def test_torrent_toolbar_tooltips(app):
    """Test that toolbar actions have correct tooltips."""
    client = TransmissionClient()

    actions = client.torrent_toolbar.actions()

    expected_tooltips = [
        "Open torrent file (not available in read-only client)",
        "",  # separator
        "Start torrent (Ctrl+S)",
        "Force start torrent (Ctrl+Shift+S)",
        "Pause torrent (Ctrl+P)",
        "",  # separator
        "Delete torrent (not available in read-only client)",
    ]

    actual_tooltips = [action.toolTip() for action in actions]
    assert actual_tooltips == expected_tooltips, (
        f"Expected {expected_tooltips}, got {actual_tooltips}"
    )


def test_torrent_toolbar_trigger_methods(app):
    """Test that toolbar actions trigger correct methods."""
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

    # Create a mock item for table
    from PySide6.QtWidgets import QTableWidgetItem

    item = QTableWidgetItem("Test Torrent")
    client.table.setItem(0, 0, item)

    # Select the first row
    client.table.selectRow(0)
    client._on_table_selection_changed()

    # Get toolbar actions
    actions = client.torrent_toolbar.actions()

    # Mock the start_torrent method to track calls
    original_start = client.start_torrent
    start_called = False
    start_torrent_id = None

    def mock_start_torrent(torrent_id):
        nonlocal start_called, start_torrent_id
        start_called = True
        start_torrent_id = torrent_id

    client.start_torrent = mock_start_torrent

    # Trigger Start action (index 2, after Open and separator)
    actions[2].trigger()

    # Verify method was called with correct torrent ID
    assert start_called, "start_torrent method should be called"
    assert start_torrent_id == 1, (
        "start_torrent should be called with correct torrent ID"
    )

    # Restore original method
    client.start_torrent = original_start
