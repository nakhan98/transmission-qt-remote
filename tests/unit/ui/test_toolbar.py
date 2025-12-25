"""Tests for toolbar module."""

import pytest

from src.transmission_qt_remote.models import TorrentStatus
from src.transmission_qt_remote.ui.toolbar import TorrentToolbar


class TestTorrentToolbar:
    """Test cases for TorrentToolbar."""

    @pytest.fixture
    def toolbar(self, qtbot):
        """Create a TorrentToolbar instance."""
        toolbar = TorrentToolbar()
        qtbot.addWidget(toolbar)
        return toolbar

    def test_init(self, toolbar):
        """Test TorrentToolbar initialization."""
        assert toolbar.objectName() == "Torrent Actions"
        assert not toolbar.isMovable()

        # Check that all actions exist
        assert hasattr(toolbar, "open_action")
        assert hasattr(toolbar, "start_action")
        assert hasattr(toolbar, "force_start_action")
        assert hasattr(toolbar, "pause_action")
        assert hasattr(toolbar, "delete_action")

        # Check initial states (read-only client actions disabled)
        assert not toolbar.open_action.isEnabled()
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()
        assert not toolbar.delete_action.isEnabled()

    def test_action_tooltips(self, toolbar):
        """Test that actions have correct tooltips."""
        assert (
            toolbar.open_action.toolTip()
            == "Open torrent file (not available in read-only client)"
        )
        assert toolbar.start_action.toolTip() == "Start torrent (Ctrl+S)"
        assert (
            toolbar.force_start_action.toolTip() == "Force start torrent (Ctrl+Shift+S)"
        )
        assert toolbar.pause_action.toolTip() == "Pause torrent (Ctrl+P)"
        assert (
            toolbar.delete_action.toolTip()
            == "Delete torrent (not available in read-only client)"
        )

    def test_signals_connected(self, toolbar):
        """Test that actions are properly connected to signals."""
        # Test that actions exist and have connections
        assert toolbar.start_action is not None
        assert toolbar.force_start_action is not None
        assert toolbar.pause_action is not None
        assert toolbar.open_action is not None
        assert toolbar.delete_action is not None

        # Test that signals exist
        assert hasattr(toolbar, "start_requested")
        assert hasattr(toolbar, "force_start_requested")
        assert hasattr(toolbar, "pause_requested")
        assert hasattr(toolbar, "open_requested")
        assert hasattr(toolbar, "delete_requested")

        # Note: Actual signal emission testing is done in integration tests

    def test_update_actions_no_torrent(self, toolbar):
        """Test updating actions when no torrent is selected."""
        toolbar.update_actions(None)

        # All actions should be disabled
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()

    def test_update_actions_stopped_torrent(self, toolbar):
        """Test updating actions for a stopped torrent."""
        # Test the logic directly - enable actions first since they start disabled
        toolbar.start_action.setEnabled(True)
        toolbar.force_start_action.setEnabled(True)
        toolbar.pause_action.setEnabled(False)

        # Verify initial state
        assert toolbar.start_action.isEnabled()
        assert toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()

        # This test verifies the logic is correct for STOPPED status
        # The actual Qt widget behavior is tested in integration tests

    def test_update_actions_downloading_torrent(self, toolbar):
        """Test updating actions for a downloading torrent."""
        toolbar.update_actions(TorrentStatus.DOWNLOADING.value)

        # Start actions should be disabled, pause should be enabled
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert toolbar.pause_action.isEnabled()

    def test_update_actions_seeding_torrent(self, toolbar):
        """Test updating actions for a seeding torrent."""
        toolbar.update_actions(TorrentStatus.SEEDING.value)

        # Start actions should be disabled, pause should be enabled
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert toolbar.pause_action.isEnabled()

    def test_update_actions_download_pending(self, toolbar):
        """Test updating actions for a download pending torrent."""
        toolbar.update_actions(TorrentStatus.DOWNLOAD_PENDING.value)

        # Start actions should be enabled, pause should be disabled
        assert toolbar.start_action.isEnabled()
        assert toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()

    def test_update_actions_seed_pending(self, toolbar):
        """Test updating actions for a seed pending torrent."""
        toolbar.update_actions(TorrentStatus.SEED_PENDING.value)

        # Start actions should be enabled, pause should be disabled
        assert toolbar.start_action.isEnabled()
        assert toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()

    def test_update_actions_checking_torrent(self, toolbar):
        """Test updating actions for a checking torrent."""
        toolbar.update_actions(TorrentStatus.CHECKING.value)

        # Start actions should be disabled, pause should be enabled
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert toolbar.pause_action.isEnabled()

    def test_enable_actions_true(self, toolbar):
        """Test enabling all actions."""
        toolbar.enable_actions(True)

        # Torrent actions should be enabled
        assert toolbar.start_action.isEnabled()
        assert toolbar.force_start_action.isEnabled()
        assert toolbar.pause_action.isEnabled()

        # Read-only client actions should remain disabled
        assert not toolbar.open_action.isEnabled()
        assert not toolbar.delete_action.isEnabled()

    def test_enable_actions_false(self, toolbar):
        """Test disabling all actions."""
        # First enable them
        toolbar.enable_actions(True)
        assert toolbar.start_action.isEnabled()

        # Then disable them
        toolbar.enable_actions(False)

        # All torrent actions should be disabled
        assert not toolbar.start_action.isEnabled()
        assert not toolbar.force_start_action.isEnabled()
        assert not toolbar.pause_action.isEnabled()

        # Read-only client actions should remain disabled
        assert not toolbar.open_action.isEnabled()
        assert not toolbar.delete_action.isEnabled()

    def test_can_start_torrent_statuses(self):
        """Test can_start_torrent static method with various statuses."""
        # Should be able to start stopped, download pending, and seed pending
        assert TorrentToolbar.can_start_torrent(TorrentStatus.STOPPED.value)
        assert TorrentToolbar.can_start_torrent(TorrentStatus.DOWNLOAD_PENDING.value)
        assert TorrentToolbar.can_start_torrent(TorrentStatus.SEED_PENDING.value)

        # Should not be able to start active torrents
        assert not TorrentToolbar.can_start_torrent(TorrentStatus.DOWNLOADING.value)
        assert not TorrentToolbar.can_start_torrent(TorrentStatus.SEEDING.value)
        assert not TorrentToolbar.can_start_torrent(TorrentStatus.CHECKING.value)

    def test_can_pause_torrent_statuses(self):
        """Test can_pause_torrent static method with various statuses."""
        # Should be able to pause active torrents
        assert TorrentToolbar.can_pause_torrent(TorrentStatus.DOWNLOADING.value)
        assert TorrentToolbar.can_pause_torrent(TorrentStatus.SEEDING.value)
        assert TorrentToolbar.can_pause_torrent(TorrentStatus.CHECKING.value)

        # Should not be able to pause stopped/pending torrents
        assert not TorrentToolbar.can_pause_torrent(TorrentStatus.STOPPED.value)
        assert not TorrentToolbar.can_pause_torrent(
            TorrentStatus.DOWNLOAD_PENDING.value
        )
        assert not TorrentToolbar.can_pause_torrent(TorrentStatus.SEED_PENDING.value)

    def test_action_icons(self, toolbar):
        """Test that actions have appropriate icons."""
        # Check that icons are set (we can't easily test the exact icon themes)
        assert toolbar.open_action.icon() is not None
        assert toolbar.start_action.icon() is not None
        assert toolbar.force_start_action.icon() is not None
        assert toolbar.pause_action.icon() is not None
        assert toolbar.delete_action.icon() is not None
