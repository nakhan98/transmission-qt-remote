# Transmission Qt Remote

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-red.svg)]()

> **⚠️ ALPHA SOFTWARE**: This is alpha-quality software under active development.
> Not recommended for critical use. Currently supports viewing and basic torrent
> control (start/pause/verify) only. Adding and deleting torrents not yet supported.

TransmissionQtRemote is a graphical user interface (GUI) application for
**monitoring and basic control** of a Transmission torrent server. Built using
PySide6, this client allows you to view torrent details and perform basic operations
like start/pause/verify. It is under active development with plans to become a
full-featured client.

## Current Limitations

This is alpha software with limited functionality:

**✅ Currently Supported:**
- View torrent details (name, status, size, speeds, peers, trackers)
- Start/pause/verify existing torrents
- Real-time monitoring and statistics
- Connection management and server configuration
- Secure credential storage

**❌ Not Yet Implemented:**
- Adding new torrents
- Deleting torrents
- Advanced torrent settings modification
- Bandwidth limit controls
- Many other Transmission features

**Full client capabilities are planned for future releases.**

## Recent Updates

### Version 0.2.0 (December 2025)
- ✅ **Fixed macOS App Identity**: Proper display in Cmd-Tab and Dock
- ✅ **Fixed Auto-Refresh**: Torrent data updates automatically (5s intervals)
- ✅ **Enhanced CI**: Python 3.12 support with comprehensive type checking
- 📊 **Test Suite**: 146 tests passing (69 unit + 76 integration + 1 fixture)

See [CHANGELOG.md](CHANGELOG.md) for full technical details.

## Features

- **Viewing & Monitoring:**
  - Display torrent details in a table format with customizable columns
  - Real-time torrent status updates
  - Torrent details dialog with files, peers, and tracker information

- **Basic Control:**
  - Start/pause/verify torrents
  - Connection settings with auto-connect option

- **UI Features:**
  - Search and filter torrents in real-time
  - System tray integration for easy access and minimization
  - Light/Dark theme support with automatic OS detection
  - Toggle visibility of specific columns for personalized views
  - Periodic data refreshes with status bar showing last refresh time

- **Quality Assurance:**
  - Comprehensive test suite with 146 tests covering implemented functionality
  - Secure credential storage using platform-native keyring services

## API Documentation

This application interacts with the Transmission BitTorrent client's JSON-RPC
API. For detailed information about available methods, parameters, and response
formats, refer to the official Transmission RPC specification:

- [Transmission RPC API Specification](https://github.com/transmission/transmission/blob/main/docs/rpc-spec.md)

The client implements the following key RPC methods:
- `torrent-get`: Retrieve torrent information including files and statistics
- `torrent-set`: Modify torrent settings such as file priorities and wanted status
- `session-get`: Retrieve session information and configuration

## Prerequisites

- Python 3.12+ (tested with 3.12, PySide6 compatibility)
- PySide6
- python-dotenv
- IP2Location (for country lookup functionality)

## Environment Variables

- `TRANSMISSION_URL`: URL of the Transmission server (default: `http://localhost:9091/transmission/rpc`)
- `TRANSMISSION_USER`: Username for Transmission authentication.
- `TRANSMISSION_PASS`: Password for Transmission authentication.
- `IP2LOCATION_DB_PATH`: Path to the IP2Location database (default: `./IP2LOCATION-LITE-DB1.BIN`).

## Secure Credential Storage

The application supports secure credential storage using platform-native keyring services:

- **macOS**: Credentials are stored in the macOS Keychain
- **Linux**: Credentials are stored using freedesktop Secret Service (GNOME Keyring, KWallet, etc.)
- **Windows**: Credentials are stored in the Windows Credential Manager

When available, you can choose to "Remember credentials securely" in the Connection Settings dialog. This provides better security than storing credentials in environment variables, which are visible in process listings.

If secure storage is not available on your platform, the application will gracefully fall back to environment variables.

## IP2Location Database Setup

For country lookup functionality, you need the IP2Location LITE database. The application will automatically check for the database when you run it with `make run`, and download it if it's not found.

You can also manually download the database using the provided Makefile target:

```bash
make download_geoip
```

This will download and extract the free IP2Location LITE DB1 database to your project directory.

If you prefer to download it yourself:

1. Go to IP2Location LITE website: https://lite.ip2location.com/database/db1-ip-country
2. Download the free IP2Location LITE DB1 database in BIN format
3. Place the downloaded .BIN file in your project directory

You can customize the database location by setting the `IP2LOCATION_DB_PATH` environment variable.

Note: If the IP2Location database is not found, the application will still work but will display "??" for country codes.

## Installation and Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/nakhan98/transmission-qt-remote.git
    cd transmission-qt-remote
    ```

2. Use the provided Makefile to set up the virtual environment and install dependencies:

    ```bash
    make install
    ```

    This will install all required dependencies from `requirements.txt`.

3. Set up your `.env` file with the necessary environment variables.

## Usage

1. Run the application using the Makefile:

    ```bash
    make run
    ```

2. The GUI will display torrent details, and you can interact with the options provided in the menu to customize your view.

## Development

### Code Quality

The project includes automated code quality checks:

```bash
# Run linting (ruff)
make lint

# Run type checking (pyright)
make typecheck

# Run all quality checks
make lint && make typecheck
```

## Testing

The project has comprehensive test coverage with 146 tests organized into unit and integration tests. The test suite uses pytest-qt for proper Qt application lifecycle management, ensuring reliable execution across different environments.

### Test Structure

- **Unit Tests** (`tests/unit/`): 69 pure function tests that don't require Qt dependencies
- **Integration Tests** (`tests/integration/`): 76 GUI component tests requiring Qt libraries
- **Fixtures** (`tests/fixtures/`): Shared test data and utilities
- **Configuration** (`tests/conftest.py`): Shared pytest fixtures including Qt application setup

### Unit Tests

These tests don't require QT dependencies and can run in any environment. They
test pure functions like URL parsing and status code mapping:

```bash
# Run locally
make test_unit

# Run in Docker
make docker_test_unit
```

**Note:** The unit tests are designed to run independently without importing
the main application module, which avoids QT dependencies.

### Integration Tests

These tests require QT dependencies and use pytest-qt for proper Qt application
management. The test suite includes a shared `conftest.py` that provides a
session-scoped Qt application fixture, eliminating Qt singleton errors:

```bash
# Run locally (uses Qt offscreen platform)
make test_integration

# Run in Docker (uses Qt offscreen platform)
make docker_test_integration
```

**Note:** Both local and Docker integration tests use Qt's offscreen platform
(`QT_QPA_PLATFORM=offscreen`) for consistent headless GUI testing without
requiring X11/display server setup.

### Running All Tests

```bash
# Run all tests locally
make test

# Run all tests in Docker
make docker_test
```

**Test Results:** All 146 tests pass with zero Qt singleton errors, thanks to
the pytest-qt integration and proper fixture management.

## Continuous Integration

The CI pipeline provides fast feedback and comprehensive testing:

```bash
# Run linting and type checking
make lint
make typecheck

# Run unit tests (fast, no GUI required)
make test_unit

# Run integration tests (requires GUI libraries)
make test_integration
```

The CI pipeline is configured to:
1. **All branches**: Run linting, type checking, and unit tests for immediate feedback
2. **Main branch only**: Run full integration test suite after all checks pass
3. All 146 tests execute reliably using Qt offscreen platform (no Xvfb needed)

**CI Configuration:** Uses GitHub Actions with pytest-qt plugin for proper Qt lifecycle management across all environments.

## Cleaning Up

- To remove temporary files and the virtual environment, use:

    ```bash
    make clean
    ```

## Contributing

This project is in early development. Contributions are welcome! There is no
formal roadmap yet, but the general direction is to build a full-featured
Transmission client with all RPC capabilities.

## License

This project is licensed under the GNU General Public License v3.0 - see the
[LICENSE](LICENSE) file for details.

## Acknowledgments

This project was developed with the assistance of various LLM models, providers
and associated tooling.
