import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtCore import QPoint, Qt

if TYPE_CHECKING:
    from ..models.torrent_models import TorrentStatus
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import TorrentStatus
from .utils import TooltipDelegate, get_country_info

logger = logging.getLogger(__name__)


class TorrentDetailDialog(QDialog):
    """A dialog window displaying detailed information about a torrent."""

    def __init__(self, parent: Optional[QWidget], torrent: Dict[str, Any]) -> None:
        """Initializes the TorrentDetailDialog with the given torrent data.

        Args:
            parent: The parent widget.
            torrent: Dictionary containing torrent data.
        """
        super().__init__(parent)
        logger.info(
            f"Torrent details dialog opened for: {torrent.get('name', 'Unknown')}"
        )
        self.torrent = torrent
        self.setWindowTitle(f"Details: {torrent['name']}")
        self.resize(600, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # General info tab
        general_tab = QWidget()
        self.tabs.addTab(general_tab, "General")

        general_layout = QGridLayout()
        general_tab.setLayout(general_layout)

        # Add general info
        row = 0
        for label, key, formatter in [
            ("Name:", "name", lambda x: x),
            ("Status:", "status", lambda x: self.get_status_text(x)),
            ("Size:", "totalSize", lambda x: f"{x / (1024 * 1024):.2f} MB"),
            (
                "Added Date:",
                "addedDate",
                lambda x: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x)),
            ),
            ("Progress:", "percentDone", lambda x: f"{x * 100:.2f}%"),
            ("Download Speed:", "rateDownload", lambda x: f"{x / 1024:.2f} KB/s"),
            ("Upload Speed:", "rateUpload", lambda x: f"{x / 1024:.2f} KB/s"),
        ]:
            if key in torrent:
                general_layout.addWidget(QLabel(label), row, 0)
                general_layout.addWidget(QLabel(formatter(torrent[key])), row, 1)
                row += 1

        # Peers tab
        peers_tab = QWidget()
        self.tabs.addTab(peers_tab, "Peers")

        peers_layout = QVBoxLayout()
        peers_tab.setLayout(peers_layout)

        # Create peers table
        self.peers_table = QTableWidget()
        peers_layout.addWidget(self.peers_table)

        # Set delegate for tooltips
        self.peers_table.setItemDelegate(TooltipDelegate(self.peers_table))

        # Set up peers table
        peers = torrent.get("peers", [])
        self.peers_table.setRowCount(len(peers))
        self.peers_table.setColumnCount(4)  # Added Country column
        self.peers_table.setHorizontalHeaderLabels(
            ["IP Address", "Country", "Client", "Progress"]
        )
        self.peers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Fill the peers table with address, country, client, and progress
        for row, peer in enumerate(peers):
            ip_address = peer.get("address", "Unknown")
            self.peers_table.setItem(row, 0, QTableWidgetItem(ip_address))

            # Get and add country code with tooltip
            country_code, country_name = get_country_info(ip_address)
            country_item = QTableWidgetItem(country_code)
            country_item.setToolTip(country_name)
            country_item.setTextAlignment(Qt.AlignCenter)
            self.peers_table.setItem(row, 1, country_item)

            self.peers_table.setItem(
                row, 2, QTableWidgetItem(peer.get("clientName", "Unknown"))
            )
            progress = peer.get("progress", 0) * 100
            self.peers_table.setItem(row, 3, QTableWidgetItem(f"{progress:.2f}%"))

        # Files tab
        files_tab = QWidget()
        self.tabs.addTab(files_tab, "Files")

        files_layout = QVBoxLayout()
        files_tab.setLayout(files_layout)

        # Create files tree widget
        self.files_tree = QTreeWidget()
        files_layout.addWidget(self.files_tree)

        # Set up files tree
        self.files_tree.setHeaderLabels(["Name", "Size", "Progress", "Priority"])
        self.files_tree.setColumnWidth(0, 300)  # Name column wider
        self.files_tree.setColumnWidth(1, 100)  # Size column
        self.files_tree.setColumnWidth(2, 80)  # Progress column
        self.files_tree.setColumnWidth(3, 80)  # Priority column

        # Populate files tree
        try:
            self._populate_files_tree(torrent)
        except Exception as e:
            logger.error(f"Exception in _populate_files_tree: {e}")
            import traceback

            traceback.print_exc()

        # Set up context menu for files tree
        self.files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_tree.customContextMenuRequested.connect(
            self._show_files_context_menu
        )

    def _populate_files_tree(self, torrent: Dict[str, Any]) -> None:
        """Populate the files tree widget with torrent file structure.

        Args:
            torrent: Torrent data dictionary containing files and fileStats.
        """
        logger.debug(
            f"Populating files tree for torrent: {torrent.get('name', 'Unknown')}"
        )
        files = torrent.get("files", [])
        file_stats = torrent.get("fileStats", [])
        logger.debug(
            f"Files available: {'files' in torrent}, FileStats available: {'fileStats' in torrent}"
        )

        if "files" not in torrent:
            # Files field not present in response
            root_item = QTreeWidgetItem(self.files_tree)
            available_fields = list(torrent.keys())

            # Check if torrent has an error
            if "error" in torrent and torrent["error"] != 0:
                root_item.setText(
                    0, f"Torrent error: {torrent.get('errorString', 'Unknown error')}"
                )
            # Check if metadata is still downloading
            elif (
                "metadataPercentComplete" in torrent
                and torrent["metadataPercentComplete"] < 1.0
            ):
                percent = torrent["metadataPercentComplete"] * 100
                root_item.setText(
                    0, f"Downloading torrent metadata ({percent:.1f}% complete)"
                )
            # Check if server returned very few fields (API error)
            elif len(available_fields) < 5:
                root_item.setText(
                    0,
                    f"Unable to retrieve file information (API error - only {len(available_fields)} fields returned)",
                )
            # Server doesn't support files field
            else:
                root_item.setText(
                    0, "File information not supported by this Transmission server"
                )
            return

        if not files:
            # Files field present but empty - likely magnet link without metadata
            root_item = QTreeWidgetItem(self.files_tree)
            root_item.setText(
                0, "No file information available (torrent metadata not downloaded yet)"
            )
            return

        # Create root item for torrent
        root_item = QTreeWidgetItem(self.files_tree)
        root_item.setText(0, torrent.get("name", "Torrent"))
        root_item.setExpanded(True)

        # Build directory structure
        dir_structure = {}

        for i, file_info in enumerate(files):
            file_path = file_info.get("name", "")
            file_size = file_info.get("length", 0)
            bytes_completed = file_info.get("bytesCompleted", 0)

            # Get file stats if available
            priority = "Normal"
            wanted = True
            if i < len(file_stats):
                stat = file_stats[i]
                wanted = stat.get("wanted", True)
                priority_val = stat.get("priority", 0)
                if priority_val == -1:
                    priority = "Low"
                elif priority_val == 1:
                    priority = "High"
                else:
                    priority = "Normal"

            # Calculate progress
            progress = (bytes_completed / file_size * 100) if file_size > 0 else 0

            # Split path into components
            path_parts = file_path.split("/")
            current_dir = dir_structure

            # Build directory hierarchy
            for part in path_parts[:-1]:  # All parts except the filename
                if part not in current_dir:
                    current_dir[part] = {}
                current_dir = current_dir[part]

            # Add file to the deepest directory
            file_name = path_parts[-1]
            current_dir[file_name] = {
                "size": file_size,
                "progress": progress,
                "priority": priority,
                "wanted": wanted,
                "is_file": True,
            }

        # Recursively build tree items
        self._build_tree_items(root_item, dir_structure)

    def _build_tree_items(
        self, parent_item: QTreeWidgetItem, structure: Dict[str, Any]
    ) -> None:
        """Recursively build tree widget items from directory structure.

        Args:
            parent_item: Parent tree widget item.
            structure: Directory structure dictionary.
        """
        for name, data in sorted(structure.items()):
            item = QTreeWidgetItem(parent_item)
            item.setText(0, name)

            if isinstance(data, dict) and data.get("is_file"):
                # This is a file
                size_mb = data["size"] / (1024 * 1024)
                item.setText(1, f"{size_mb:.2f} MB")
                item.setText(2, f"{data['progress']:.1f}%")
                item.setText(3, data["priority"])

                # Set text alignment for numeric columns
                item.setTextAlignment(1, Qt.AlignRight)
                item.setTextAlignment(2, Qt.AlignRight)
            else:
                # This is a directory, calculate totals
                total_size, total_progress, file_count = (
                    self._calculate_directory_stats(data)
                )
                size_mb = total_size / (1024 * 1024)
                avg_progress = total_progress / file_count if file_count > 0 else 0

                item.setText(1, f"{size_mb:.2f} MB")
                item.setText(2, f"{avg_progress:.1f}%")
                item.setText(3, "")

                # Set text alignment for numeric columns
                item.setTextAlignment(1, Qt.AlignRight)
                item.setTextAlignment(2, Qt.AlignRight)

                # Recursively add children
                self._build_tree_items(item, data)

    def _calculate_directory_stats(
        self, structure: Dict[str, Any]
    ) -> tuple[int, float, int]:
        """Calculate total size, average progress, and file count for a directory.

        Args:
            structure: Directory structure dictionary.

        Returns:
            Tuple of (total_size, total_progress, file_count).
        """
        total_size = 0
        total_progress = 0.0
        file_count = 0

        for _name, data in structure.items():
            if isinstance(data, dict) and data.get("is_file"):
                total_size += data["size"]
                total_progress += data["progress"]
                file_count += 1
            elif isinstance(data, dict):
                # Recursively calculate subdirectory stats
                sub_size, sub_progress, sub_count = self._calculate_directory_stats(
                    data
                )
                total_size += sub_size
                total_progress += sub_progress
                file_count += sub_count

        return total_size, total_progress, file_count

    def _show_files_context_menu(self, position: "QPoint") -> None:  # type: ignore[name-defined]
        """Show context menu for files tree widget.

        Args:
            position: Position where context menu was requested.
        """
        item = self.files_tree.itemAt(position)
        if not item:
            return

        # Only show context menu for files (not directories)
        file_path = self._get_item_file_path(item)
        if not file_path:
            return

        menu = QMenu(self)

        # Priority actions
        priority_menu = menu.addMenu("Set Priority")
        low_action = priority_menu.addAction("Low")
        normal_action = priority_menu.addAction("Normal")
        high_action = priority_menu.addAction("High")

        menu.addSeparator()

        # Wanted/Unwanted actions
        wanted_action = menu.addAction("Want File")
        unwanted_action = menu.addAction("Don't Want File")

        # Connect actions
        low_action.triggered.connect(lambda: self._set_file_priority(file_path, -1))
        normal_action.triggered.connect(lambda: self._set_file_priority(file_path, 0))
        high_action.triggered.connect(lambda: self._set_file_priority(file_path, 1))
        wanted_action.triggered.connect(lambda: self._set_file_wanted(file_path, True))
        unwanted_action.triggered.connect(
            lambda: self._set_file_wanted(file_path, False)
        )

        menu.exec(self.files_tree.mapToGlobal(position))

    def _get_item_file_path(self, item: QTreeWidgetItem) -> Optional[str]:
        """Get the full file path for a tree item.

        Args:
            item: Tree widget item.

        Returns:
            Full file path or None if item is not a file.
        """
        if not item:
            return None

        # Build path by walking up the tree
        path_parts = []
        current = item
        while current:
            path_parts.insert(0, current.text(0))
            current = current.parent()

        # Remove root torrent name
        if len(path_parts) > 1:
            return "/".join(path_parts[1:])
        return None

    def _set_file_priority(self, file_path: str, priority: int) -> None:
        """Set priority for a specific file.

        Args:
            file_path: Path to the file within the torrent.
            priority: Priority value (-1=Low, 0=Normal, 1=High).
        """
        # Find file index
        file_index = self._get_file_index(file_path)
        if file_index is None:
            return

        # Make API call to set file priority
        if hasattr(self.parent(), "set_file_priority"):
            success = self.parent().set_file_priority(
                self.torrent["id"], [file_index], priority
            )
            if success:
                self._update_file_display(file_path, priority=priority)

    def _set_file_wanted(self, file_path: str, wanted: bool) -> None:
        """Set wanted status for a specific file.

        Args:
            file_path: Path to the file within the torrent.
            wanted: Whether the file should be wanted.
        """
        # Find file index
        file_index = self._get_file_index(file_path)
        if file_index is None:
            return

        # Make API call to set file wanted status
        if hasattr(self.parent(), "set_file_wanted"):
            success = self.parent().set_file_wanted(
                self.torrent["id"], [file_index], wanted
            )
            if success:
                # Refresh the torrent data to get updated file stats
                if hasattr(self.parent(), "fetch_torrent_details"):
                    updated_torrent = self.parent().fetch_torrent_details(
                        self.torrent["id"]
                    )
                    if updated_torrent:
                        self.torrent = updated_torrent
                        self.files_tree.clear()
                        self._populate_files_tree(self.torrent)

    def _get_file_index(self, file_path: str) -> Optional[int]:
        """Get the file index for a given file path.

        Args:
            file_path: Path to the file within the torrent.

        Returns:
            File index or None if not found.
        """
        files = self.torrent.get("files", [])
        for i, file_info in enumerate(files):
            if file_info.get("name") == file_path:
                return i
        return None

    def _update_file_display(
        self,
        file_path: str,
        priority: Optional[int] = None,
        wanted: Optional[bool] = None,
    ) -> None:
        """Update the display for a specific file.

        Args:
            file_path: Path to the file within the torrent.
            priority: New priority value if being updated.
            wanted: New wanted status if being updated.
        """

        # Find the tree item for this file
        def find_item_by_path(
            parent: "QTreeWidgetItem", target_path: str
        ) -> "Optional[QTreeWidgetItem]":  # type: ignore[name-defined]
            for i in range(parent.childCount()):
                child = parent.child(i)
                item_path = self._get_item_file_path(child)
                if item_path == target_path:
                    return child
                # Recursively search in subdirectories
                result = find_item_by_path(child, target_path)
                if result:
                    return result
            return None

        root = self.files_tree.invisibleRootItem()
        item = find_item_by_path(root, file_path)
        if item and priority is not None:
            if priority == -1:
                item.setText(3, "Low")
            elif priority == 1:
                item.setText(3, "High")
            else:
                item.setText(3, "Normal")

    def get_status_text(self, status: int) -> str:
        """Converts a status code to a human-readable string.

        Args:
            status: The status code of the torrent.

        Returns:
            The corresponding status text.
        """
        try:
            torrent_status = TorrentStatus(status)
            return torrent_status.display_text()
        except ValueError:
            return "Unknown"
