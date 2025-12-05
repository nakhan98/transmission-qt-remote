from typing import Callable, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config_manager import ConfigManager
from ..credential_manager import CredentialManager


class ConnectionSettingsDialog(QDialog):
    """Dialog for editing Transmission connection settings."""

    def __init__(
        self,
        parent: Optional[QWidget],
        current_url: str,
        use_credentials: bool,
        username: str,
        password: str,
        refresh_interval_sec: int,
        minimized_interval_sec: int,
        connection_timeout_sec: int,
        test_callback: Callable[[str, Optional[str], Optional[str]], Tuple[bool, str]],
        remember_credentials: bool = False,
        auto_connect_enabled: bool = False,
    ) -> None:
        """Initialize with current connection values and a test callback."""
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._test_callback = test_callback
        self._refresh_interval_sec = refresh_interval_sec
        self._minimized_interval_sec = minimized_interval_sec
        self._connection_timeout_sec = connection_timeout_sec

        # Store current server info for backward compatibility
        self.current_url = current_url
        self.use_credentials = use_credentials
        self.username = username
        self.password = password
        self.remember_credentials = remember_credentials
        self.auto_connect_enabled = auto_connect_enabled

        # Initialize config manager for server persistence
        self._config_manager = ConfigManager()

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # General tab
        self._create_general_tab()

        # Servers tab
        self._create_servers_tab()

        # Dialog buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self._on_ok)
        self.cancel_button.clicked.connect(self.reject)

    def _create_general_tab(self) -> None:
        """Create the General settings tab."""
        general_widget = QWidget()
        self.tab_widget.addTab(general_widget, "General")

        layout = QVBoxLayout()
        general_widget.setLayout(layout)

        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Refresh interval
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setMinimum(5)
        self.refresh_spin.setMaximum(120)
        self.refresh_spin.setSuffix(" sec")
        self.refresh_spin.setValue(self._refresh_interval_sec)
        form_layout.addRow("Refresh interval:", self.refresh_spin)

        # Minimized interval
        self.minimized_spin = QSpinBox()
        self.minimized_spin.setMinimum(10)
        self.minimized_spin.setMaximum(300)
        self.minimized_spin.setSuffix(" sec")
        self.minimized_spin.setValue(self._minimized_interval_sec)
        form_layout.addRow("Minimized interval:", self.minimized_spin)

        # Connection timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setSuffix(" sec")
        self.timeout_spin.setValue(self._connection_timeout_sec)
        form_layout.addRow("Connection timeout:", self.timeout_spin)

        # Auto-connect checkbox
        self.auto_connect_checkbox = QCheckBox("Auto-connect on startup")
        self.auto_connect_checkbox.setChecked(self.auto_connect_enabled)
        self.auto_connect_checkbox.setToolTip(
            "Automatically connect to the last used server when the application starts"
        )
        layout.addWidget(self.auto_connect_checkbox)

        layout.addStretch()

    def _create_servers_tab(self) -> None:
        """Create the Servers management tab."""
        servers_widget = QWidget()
        self.tab_widget.addTab(servers_widget, "Servers")

        layout = QVBoxLayout()
        servers_widget.setLayout(layout)

        # Server list
        self.server_list = QListWidget()
        layout.addWidget(self.server_list)

        # Buttons for server management
        button_layout = QHBoxLayout()
        self.add_server_btn = QPushButton("Add Server")
        self.edit_server_btn = QPushButton("Edit Server")
        self.delete_server_btn = QPushButton("Delete Server")
        self.test_server_btn = QPushButton("Test Connection")

        button_layout.addWidget(self.add_server_btn)
        button_layout.addWidget(self.edit_server_btn)
        button_layout.addWidget(self.delete_server_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.test_server_btn)

        layout.addLayout(button_layout)

        # Connect button signals
        self.add_server_btn.clicked.connect(self._add_server)
        self.edit_server_btn.clicked.connect(self._edit_server)
        self.delete_server_btn.clicked.connect(self._delete_server)
        self.test_server_btn.clicked.connect(self._test_selected_server)
        self.server_list.itemSelectionChanged.connect(self._update_button_states)

        # Initialize with current server for backward compatibility
        self._initialize_servers()

    def _initialize_servers(self) -> None:
        """Initialize the server list from config or current connection."""
        servers = self._config_manager.get_servers()

        if servers:
            # Load configured servers
            for server in servers:
                # Load credentials from keyring if available
                if server.get("use_credentials") and server.get("remember_credentials"):
                    stored_password = CredentialManager.get_credentials(
                        server.get("username", "")
                    )
                    if stored_password:
                        server = server.copy()  # Don't modify the original
                        server["password"] = stored_password

                # Format server display text with last connected info
                display_text = f"{server['name']} - {server['url']}"
                last_connected = server.get("last_connected")
                if last_connected:
                    import time

                    try:
                        date_str = time.strftime(
                            "%Y-%m-%d %H:%M", time.localtime(last_connected)
                        )
                        display_text += f" (last: {date_str})"
                    except (ValueError, OSError):
                        pass
                connection_count = server.get("connection_count", 0)
                if connection_count > 0:
                    display_text += f" [{connection_count} connections]"

                item = QListWidgetItem(display_text)
                item.setData(1, server)
                self.server_list.addItem(item)
        else:
            # Fall back to current connection for backward compatibility
            item = QListWidgetItem(f"Default Server - {self.current_url}")
            item.setData(
                1,
                {
                    "name": "Default Server",
                    "url": self.current_url,
                    "use_credentials": self.use_credentials,
                    "username": self.username,
                    "password": self.password,
                    "remember_credentials": self.remember_credentials,
                },
            )
            self.server_list.addItem(item)

        # Select first item if available
        if self.server_list.count() > 0:
            self.server_list.setCurrentItem(self.server_list.item(0))

    def _add_server(self) -> None:
        """Add a new server configuration."""
        # Create a simple dialog for adding a server
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Server")
        dialog.setModal(True)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., My Home Server")
        layout.addRow("Server Name:", name_edit)

        url_edit = QLineEdit()
        url_edit.setPlaceholderText("http://localhost:9091/transmission/rpc")
        layout.addRow("Server URL:", url_edit)

        auth_checkbox = QCheckBox("Use authentication")
        layout.addRow(auth_checkbox)

        username_edit = QLineEdit()
        username_edit.setEnabled(False)
        layout.addRow("Username:", username_edit)

        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setEnabled(False)
        layout.addRow("Password:", password_edit)

        remember_checkbox = QCheckBox("Remember credentials securely")
        remember_checkbox.setEnabled(False)
        layout.addRow(remember_checkbox)

        def toggle_auth():
            enabled = auth_checkbox.isChecked()
            username_edit.setEnabled(enabled)
            password_edit.setEnabled(enabled)
            remember_checkbox.setEnabled(enabled and CredentialManager.is_available())

        auth_checkbox.stateChanged.connect(toggle_auth)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            url = url_edit.text().strip()

            if not name or not url:
                QMessageBox.warning(
                    self, "Invalid Input", "Please provide both server name and URL."
                )
                return

            # Create server data (passwords are stored in keyring, not config)
            server_data = {
                "name": name,
                "url": url,
                "use_credentials": auth_checkbox.isChecked(),
                "username": username_edit.text().strip()
                if auth_checkbox.isChecked()
                else "",
                "password": "",  # Never store passwords in config file
                "remember_credentials": remember_checkbox.isChecked()
                if auth_checkbox.isChecked()
                else False,
                "last_connected": None,  # Will be set on successful connection
                "connection_count": 0,
            }

            # Store credentials if requested
            if (
                server_data["use_credentials"]
                and server_data["remember_credentials"]
                and CredentialManager.is_available()
            ):
                if not CredentialManager.set_credentials(
                    server_data["username"], password_edit.text()
                ):
                    QMessageBox.warning(
                        self,
                        "Credential Storage Failed",
                        "Failed to store credentials securely. They will not be remembered.",
                    )

            # Add to server list
            item = QListWidgetItem(f"{name} - {url}")
            item.setData(1, server_data)
            self.server_list.addItem(item)

            # Save to config
            self._config_manager.add_server(server_data)

            QMessageBox.information(
                self, "Server Added", f"Server '{name}' has been added."
            )

    def _edit_server(self) -> None:
        """Edit the selected server configuration."""
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a server to edit.")
            return

        server_data = current_item.data(1)
        if not server_data:
            QMessageBox.warning(
                self, "Invalid Data", "Selected server has invalid data."
            )
            return

        # Create edit dialog (similar to add dialog but pre-populated)
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Server")
        dialog.setModal(True)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit(server_data["name"])
        layout.addRow("Server Name:", name_edit)

        url_edit = QLineEdit(server_data["url"])
        layout.addRow("Server URL:", url_edit)

        auth_checkbox = QCheckBox("Use authentication")
        auth_checkbox.setChecked(server_data["use_credentials"])
        layout.addRow(auth_checkbox)

        username_edit = QLineEdit(server_data["username"])
        username_edit.setEnabled(server_data["use_credentials"])
        layout.addRow("Username:", username_edit)

        # Load password from keyring if credentials are remembered
        password_value = ""
        if (
            server_data["use_credentials"]
            and server_data.get("remember_credentials")
            and CredentialManager.is_available()
        ):
            stored_password = CredentialManager.get_credentials(server_data["username"])
            if stored_password:
                password_value = stored_password

        password_edit = QLineEdit(password_value)
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setEnabled(server_data["use_credentials"])
        layout.addRow("Password:", password_edit)

        remember_checkbox = QCheckBox("Remember credentials securely")
        remember_checkbox.setChecked(server_data.get("remember_credentials", False))
        remember_checkbox.setEnabled(
            server_data["use_credentials"] and CredentialManager.is_available()
        )
        layout.addRow(remember_checkbox)

        def toggle_auth():
            enabled = auth_checkbox.isChecked()
            username_edit.setEnabled(enabled)
            password_edit.setEnabled(enabled)
            remember_checkbox.setEnabled(enabled and CredentialManager.is_available())

        auth_checkbox.stateChanged.connect(toggle_auth)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            url = url_edit.text().strip()

            if not name or not url:
                QMessageBox.warning(
                    self, "Invalid Input", "Please provide both server name and URL."
                )
                return

            # Update server data
            updated_data = {
                "name": name,
                "url": url,
                "use_credentials": auth_checkbox.isChecked(),
                "username": username_edit.text().strip()
                if auth_checkbox.isChecked()
                else "",
                "password": "",  # Never store passwords in config file
                "remember_credentials": remember_checkbox.isChecked()
                if auth_checkbox.isChecked()
                else False,
            }

            # Store credentials if requested and changed
            if (
                updated_data["use_credentials"]
                and updated_data["remember_credentials"]
                and CredentialManager.is_available()
            ):
                if not CredentialManager.set_credentials(
                    updated_data["username"], password_edit.text()
                ):
                    QMessageBox.warning(
                        self,
                        "Credential Storage Failed",
                        "Failed to store credentials securely. They will not be remembered.",
                    )

            # Update the list item
            current_item.setText(f"{name} - {url}")
            current_item.setData(1, updated_data)

            # Save to config
            old_server_data = current_item.data(1)
            self._config_manager.update_server(old_server_data["name"], updated_data)

            QMessageBox.information(
                self, "Server Updated", f"Server '{name}' has been updated."
            )

    def _delete_server(self) -> None:
        """Delete the selected server configuration."""
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select a server to delete."
            )
            return

        server_data = current_item.data(1)
        if not server_data:
            QMessageBox.warning(
                self, "Invalid Data", "Selected server has invalid data."
            )
            return

        # Check if this is the default server (for now, allow deletion but warn)
        server_name = server_data["name"]

        reply = QMessageBox.question(
            self,
            "Delete Server",
            f"Are you sure you want to delete the server '{server_name}'?\n\n"
            + "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Remove from list
            row = self.server_list.row(current_item)
            self.server_list.takeItem(row)

            # Remove from config
            self._config_manager.remove_server(server_name)

            # Note: In a full implementation, we'd also need to clean up stored credentials
            # But for now, we'll leave them in keyring in case user wants to re-add

            QMessageBox.information(
                self, "Server Deleted", f"Server '{server_name}' has been deleted."
            )

    def _test_selected_server(self) -> None:
        """Test connection to the selected server."""
        current_item = self.server_list.currentItem()
        if not current_item:
            return

        server_data = current_item.data(1)
        if not server_data:
            return

        # Extract server details
        url = server_data["url"]
        use_credentials = server_data["use_credentials"]
        username = server_data["username"] if use_credentials else None

        # Load password from keyring if credentials are configured to be remembered
        password = None
        if use_credentials and server_data.get("remember_credentials"):
            password = CredentialManager.get_credentials(username or "")

        success, message = self._test_callback(url, username, password)

        if success:
            QMessageBox.information(self, "Connection OK", message)
        else:
            QMessageBox.warning(self, "Connection Failed", message)

    def _update_button_states(self) -> None:
        """Update button enabled states based on selection."""
        has_selection = self.server_list.currentItem() is not None
        self.edit_server_btn.setEnabled(has_selection)
        self.delete_server_btn.setEnabled(has_selection)
        self.test_server_btn.setEnabled(has_selection)

    def _run_test(self, show_success_message: bool) -> bool:
        # Test the current/default server connection
        url = self.current_url
        if not url:
            QMessageBox.warning(self, "Invalid URL", "No server URL configured.")
            return False

        use_credentials = self.use_credentials
        username = self.username if use_credentials else None
        password = self.password if use_credentials else None

        success, message = self._test_callback(url, username, password)

        if success and show_success_message:
            QMessageBox.information(self, "Connection OK", message)
        elif not success:
            QMessageBox.warning(self, "Connection Failed", message)

        return success

    def _on_ok(self) -> None:
        # Just accept the dialog - connection testing is done via individual server test buttons
        self.accept()

    def get_settings(self) -> Tuple[str, bool, str, str, int, int, int, bool, bool]:
        return (
            self.current_url,  # For backward compatibility
            self.use_credentials,  # For backward compatibility
            self.username,  # For backward compatibility
            self.password,  # For backward compatibility
            self.refresh_spin.value(),
            self.minimized_spin.value(),
            self.timeout_spin.value(),
            self.remember_credentials,  # For backward compatibility
            self.auto_connect_checkbox.isChecked(),
        )
