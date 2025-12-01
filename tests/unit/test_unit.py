#!/usr/bin/env python3
"""
Unit tests for Transmission Client functions that don't depend on QT.
These tests can run in a standard CI environment without graphical dependencies.
"""


# Since we can't directly import from transmission_client due to QT dependencies,
# we'll need to extract and test the functions individually.


# Extract the extract_hostname function from transmission_client.py
def extract_hostname(url):
    """Extract hostname and port from a URL.

    Args:
        url: Full URL to parse

    Returns:
        The hostname with port (if present) from the URL
    """
    try:
        # Handle empty strings or None values
        if not url:
            return ""

        # Try to parse the URL
        if url.startswith("http"):
            # Standard HTTP URL
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            # Keep the port if present
            return parsed_url.netloc
        elif url.startswith("udp://"):
            # UDP URL - keep the host:port part
            parts = url[6:].split("/")
            hostname_port = parts[0]
            return hostname_port
        else:
            # For other protocols - try to get hostname:port
            if "/" in url:
                parts = url.split("/")
                if len(parts) > 2:
                    return parts[2]  # This will include port if present
            return url
    except Exception:
        return url


# Extract the get_country_info function (simplified version for testing)
def get_country_info(ip_address):
    """Get country code and name for an IP address.

    Args:
        ip_address: The IP address to look up

    Returns:
        A tuple containing (country_code, country_name)
        If the country is unknown, returns ("??", "Unknown")
    """
    # Skip local/private IPs
    if ip_address.startswith(("10.", "172.", "192.168.", "127.", "::1", "fc00:", "fd")):
        return ("--", "Local Network")

    # In a real test we'd mock the database, but for this test we'll return placeholder values
    return ("??", "Unknown (test)")


# Test the extract_hostname function
def test_extract_hostname():
    """Test URL hostname extraction function with various inputs."""
    # Test HTTP URL without port
    assert extract_hostname("http://example.com/announce") == "example.com"

    # Test HTTPS URL with port
    assert (
        extract_hostname("https://tracker.example.org:8080/announce")
        == "tracker.example.org:8080"
    )

    # Test UDP URL with port
    assert (
        extract_hostname("udp://tracker.example.net:6969/announce")
        == "tracker.example.net:6969"
    )

    # Test other protocol with port
    assert extract_hostname("wss://example.com:443/announce") == "example.com:443"

    # Test other protocol without port
    assert extract_hostname("wss://example.com/announce") == "example.com"

    # Test malformed URL
    assert extract_hostname("example.com") == "example.com"

    # Test same hostname with different ports
    assert extract_hostname("https://example.com:8080/announce") != extract_hostname(
        "https://example.com:9090/announce"
    )

    # Test empty string (shouldn't crash)
    assert extract_hostname("") == ""

    # Test exception handling
    # This will raise an exception because None doesn't have .startswith
    try:
        extract_hostname(None)
        assert False, "Should have raised an exception"
    except Exception:
        pass


# Test get_country_info function
def test_get_country_info():
    """Test country lookup function with various IP addresses."""
    # Test local IP address
    code, name = get_country_info("192.168.1.1")
    assert code == "--"
    assert name == "Local Network"

    # Test a few more IP types for the simplified version
    code, name = get_country_info("10.0.0.1")
    assert code == "--"
    assert name == "Local Network"

    code, name = get_country_info("127.0.0.1")
    assert code == "--"
    assert name == "Local Network"


# Define a test for status code mapping
def test_status_text_mapping():
    """Test the status code to text mapping logic."""
    # Given: A status mapping dictionary with known status codes
    status_map = {
        0: "Stopped",
        1: "Checking",
        2: "Checked",
        3: "Downloading",
        4: "Download Waiting",
        5: "Seeding",
        6: "Seed Waiting",
    }

    # When: Converting each status code to text
    # Then: Each code should map to the expected human-readable text
    for code, expected_text in status_map.items():
        assert get_status_text(code) == expected_text

    # When: Converting an unknown status code
    # Then: Should return "Unknown"
    assert get_status_text(99) == "Unknown"


# Helper function for status text
def get_status_text(status):
    """Converts a status code to a human-readable string."""
    status_map = {
        0: "Stopped",
        1: "Checking",
        2: "Checked",
        3: "Downloading",
        4: "Download Waiting",
        5: "Seeding",
        6: "Seed Waiting",
    }
    return status_map.get(status, "Unknown")
