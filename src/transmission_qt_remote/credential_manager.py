"""
Secure Credential Storage Manager

This module provides secure credential storage using the keyring library,
which leverages platform-native secure storage mechanisms (macOS Keychain,
Linux Secret Service, Windows Credential Manager).
"""

import logging
from typing import Optional

try:
    import keyring
    from keyring.errors import PasswordDeleteError

    has_keyring = True
except ImportError:
    keyring = None
    has_keyring = False

    # Create a custom exception class for password delete errors
    class PasswordDeleteError(Exception):
        pass


logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Secure credential storage manager using platform-native keyring services.

    Provides a simple interface for storing and retrieving Transmission
    authentication credentials securely.
    """

    # Service name derived from app name for consistency
    # Avoid circular import by defining locally
    APP_NAME = "Transmission QT Remote"
    SERVICE_NAME = APP_NAME.lower().replace(" ", "-")

    @staticmethod
    def is_available() -> bool:
        """Check if secure credential storage is available on this platform."""
        return has_keyring

    @staticmethod
    def set_credentials(username: str, password: str) -> bool:
        """
        Store credentials securely.

        Args:
            username: Transmission username
            password: Transmission password

        Returns:
            True if credentials were stored successfully, False otherwise
        """
        if not has_keyring:
            logger.warning("Keyring not available - cannot store credentials securely")
            return False

        try:
            keyring.set_password(CredentialManager.SERVICE_NAME, username, password)  # type: ignore[union-attr]
            logger.info(f"Credentials stored securely for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    @staticmethod
    def get_credentials(username: str) -> Optional[str]:
        """
        Retrieve credentials securely.

        Args:
            username: Transmission username

        Returns:
            Password if found, None if not found or on error
        """
        if not has_keyring:
            logger.warning("Keyring not available - cannot retrieve credentials")
            return None

        try:
            password = keyring.get_password(CredentialManager.SERVICE_NAME, username)  # type: ignore[union-attr]
            if password:
                logger.info(f"Credentials retrieved for user: {username}")
            else:
                logger.debug(f"No credentials found for user: {username}")
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None

    @staticmethod
    def delete_credentials(username: str) -> bool:
        """
        Remove credentials from secure storage.

        Args:
            username: Transmission username

        Returns:
            True if credentials were deleted successfully, False otherwise
        """
        if not has_keyring:
            logger.warning("Keyring not available - cannot delete credentials")
            return False

        try:
            keyring.delete_password(CredentialManager.SERVICE_NAME, username)  # type: ignore[union-attr]
            logger.info(f"Credentials deleted for user: {username}")
            return True
        except PasswordDeleteError:
            logger.debug(f"No credentials found to delete for user: {username}")
            return True  # Not an error if credentials don't exist
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    @staticmethod
    def has_credentials(username: str) -> bool:
        """
        Check if credentials exist for the given username.

        Args:
            username: Transmission username

        Returns:
            True if credentials exist, False otherwise
        """
        return CredentialManager.get_credentials(username) is not None
