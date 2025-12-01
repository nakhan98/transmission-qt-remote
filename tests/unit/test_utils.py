"""Unit tests for dialogs/utils.py module."""

from unittest.mock import Mock, patch

from transmission_qt_remote.dialogs import utils


class TestUtils:
    """Test cases for dialog utilities."""

    def test_extract_hostname_http_url(self):
        """Test hostname extraction from HTTP URLs."""
        assert utils.extract_hostname("http://example.com") == "example.com"
        assert utils.extract_hostname("https://example.com:8080") == "example.com:8080"
        assert (
            utils.extract_hostname("http://sub.example.com/path") == "sub.example.com"
        )

    def test_extract_hostname_udp_url(self):
        """Test hostname extraction from UDP URLs."""
        assert (
            utils.extract_hostname("udp://tracker.example.com:6969")
            == "tracker.example.com:6969"
        )
        assert (
            utils.extract_hostname("udp://192.168.1.1:80/announce") == "192.168.1.1:80"
        )

    def test_extract_hostname_other_protocols(self):
        """Test hostname extraction from other protocol URLs."""
        assert utils.extract_hostname("tcp://host:1234") == "host:1234"
        assert utils.extract_hostname("host:5678/path") == "host:5678/path"

    def test_extract_hostname_edge_cases(self):
        """Test hostname extraction edge cases."""
        assert utils.extract_hostname("") == ""
        assert utils.extract_hostname("invalid") == "invalid"
        assert utils.extract_hostname("http://") == ""

    def test_get_country_info_local_ips(self):
        """Test country lookup for local/private IP addresses."""
        test_ips = [
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "127.0.0.1",
            "::1",
            "fc00::1",
            "fd00::1",
        ]

        for ip in test_ips:
            code, name = utils.get_country_info(ip)
            assert code == "--"
            assert name == "Local Network"

    @patch("transmission_qt_remote.dialogs.utils.ip2location_db")
    def test_get_country_info_with_database(self, mock_db):
        """Test country lookup when database is available."""
        # Mock the database record
        mock_record = Mock()
        mock_record.country_short = "US"
        mock_record.country_long = "United States"
        mock_db.get_all.return_value = mock_record

        code, name = utils.get_country_info("8.8.8.8")

        assert code == "US"
        assert name == "United States"
        mock_db.get_all.assert_called_once_with("8.8.8.8")

    @patch("transmission_qt_remote.dialogs.utils.ip2location_db")
    def test_get_country_info_database_unavailable(self, mock_db):
        """Test country lookup when database is not available."""
        # Temporarily set the module's ip2location_db to None
        original_db = utils.ip2location_db
        utils.ip2location_db = None

        try:
            code, name = utils.get_country_info("8.8.8.8")
            assert code == "??"
            assert "Unknown" in name
        finally:
            utils.ip2location_db = original_db

    @patch("transmission_qt_remote.dialogs.utils.ip2location_db")
    def test_get_country_info_invalid_record(self, mock_db):
        """Test country lookup when database returns invalid record."""
        mock_record = Mock()
        mock_record.country_short = "-"  # Invalid country code
        mock_record.country_long = None
        mock_db.get_all.return_value = mock_record

        code, name = utils.get_country_info("8.8.8.8")

        assert code == "??"
        assert "Unknown" in name

    @patch("transmission_qt_remote.dialogs.utils.ip2location_db")
    def test_get_country_info_database_exception(self, mock_db):
        """Test country lookup when database throws exception."""
        mock_db.get_all.side_effect = Exception("Database error")

        code, name = utils.get_country_info("8.8.8.8")

        assert code == "??"
        assert name == "Unknown"

    @patch("transmission_qt_remote.dialogs.utils.ip2location_db")
    def test_get_country_info_no_record(self, mock_db):
        """Test country lookup when database returns None."""
        mock_db.get_all.return_value = None

        code, name = utils.get_country_info("8.8.8.8")

        assert code == "??"
        assert "Unknown" in name
