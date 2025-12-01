#!/usr/bin/env python3
"""
Test script for verifying IP2Location database functionality.
"""

import logging
import os
import sys

from IP2Location import database as ip2l

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Path to database file
DB_PATH = "./IP2LOCATION-LITE-DB1.BIN"


def test_ip2location():
    """Test IP2Location database with various IP addresses."""
    if not os.path.exists(DB_PATH):
        logging.error(f"IP2Location database not found at {DB_PATH}")
        sys.exit(1)

    logging.info(f"Database file size: {os.path.getsize(DB_PATH)} bytes")

    try:
        # Initialize the database
        ip2location = ip2l.IP2Location()
        ip2location.open(DB_PATH)

        # Test IPs
        test_ips = [
            "8.8.8.8",  # Google DNS (US)
            "93.230.115.183",  # The example IP you provided
            "185.125.190.39",  # Random European IP
            "219.78.163.111",  # Random Asian IP
            "192.168.1.1",  # Private IP
            "127.0.0.1",  # Localhost
        ]

        for ip in test_ips:
            try:
                logging.info(f"Looking up IP: {ip}")
                record = ip2location.get_all(ip)

                # Print basic attributes that should be available in all databases
                try:
                    logging.info(f"  country_short: {record.country_short}")
                    logging.info(f"  country_long: {record.country_long}")
                except Exception as e:
                    logging.error(f"  Error accessing country data: {e}")

            except Exception as e:
                logging.error(f"Error looking up IP {ip}: {e}")

    except Exception as e:
        logging.error(f"Error initializing IP2Location database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_ip2location()
