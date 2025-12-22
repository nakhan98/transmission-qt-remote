# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-22

### Added
- **Major Refactoring**: Split monolithic 1,618-line `main_window.py` into 8 focused modules
  - `api/transmission_api.py` (407 lines) - HTTP RPC communication with Transmission
  - `connection/connection_manager.py` (331 lines) - Connection state and credentials
  - `models/torrent_models.py` (59 lines) - Data models and enums
  - `ui/menu_bar.py` (270 lines) - Application menu bar management
  - `ui/system_tray.py` (121 lines) - System tray functionality
  - `ui/toolbar.py` (177 lines) - Torrent action toolbar
  - `ui/torrent_table.py` (362 lines) - Table widget with filtering and display
- Comprehensive unit test coverage for all new modules (158 tests passing)
- Improved code maintainability with clear separation of concerns
- Coordinator pattern implementation in main window

### Changed
- `main_window.py` reduced from 1,618 to 555 lines (66% reduction)
- All integration tests updated to work with refactored component structure
- Enhanced type checking coverage with proper Optional handling

### Fixed
- Resolved all type checking errors (0 errors, 0 warnings)
- Fixed integration test collection and execution issues
- Improved signal connection patterns for Qt components

### Technical Details

#### Architecture Changes
- **Coordinator Pattern**: Main window now orchestrates specialized managers
- **Signal-Based Communication**: Components communicate via Qt signals
- **Dependency Injection**: Managers receive dependencies through constructor injection
- **Single Responsibility**: Each module handles one aspect of functionality

#### Module Breakdown
- **API Layer**: Clean HTTP interface with automatic session management
- **Connection Layer**: Credential management and connection state handling
- **Model Layer**: Type-safe data structures for torrent information
- **UI Layer**: Modular UI components with proper separation

## [0.2.0] - 2025-12-05

### Added
- Python 3.12 support with proper virtual environment management
- Type checking with pyright (0 errors, 0 warnings)
- Docker-based integration test verification
- QApplication metadata for proper macOS app identity
- Icon path resolution for consistent branding across launch contexts
- Automatic torrent data refresh with configurable intervals (5s normal, 30s minimized)

### Fixed
- **Critical**: macOS Cmd-Tab and Dock now display "Transmission QT Remote" instead of "python3.12"
- **Critical**: Torrent data now auto-refreshes after connecting (previously froze after initial fetch)
- Timer lifecycle management (start on connect, stop on disconnect)
- Config manager test expectations for updated app name

### Changed
- CI workflow uses virtual environments with uv
- System dependencies optimized (reduced from 17 to 7 packages for unit tests)
- Resolved all 128 type errors across codebase

### Technical Details

#### CI Infrastructure
- `.github/workflows/ci.yml`: Enhanced pipeline with lint, typecheck, unit, and integration tests
- All jobs now use proper virtual environment setup via Makefile
- Integration tests verified in Docker with minimal system dependencies

#### Application Fixes
- `src/transmission_qt_remote/transmission_client.py`: 
  - Added `_resolve_icon_path()` for cross-environment icon loading
  - Set QApplication name, display name, and organization metadata
  - Imported canonical `APP_NAME` and `ICON_FILE` from config.py
- `src/transmission_qt_remote/main_window.py`:
  - Connected `QTimer.timeout` to `refresh_data()` in `__init__`
  - Modified `set_timer_interval()` to start timer when connected
  - Added timer start calls after successful connections

#### Testing
- `tests/unit/test_config_manager.py`: Updated test to check for "transmission_qt_remote" directory name
- All 146 tests passing (69 unit + 76 integration + 1 fixture)

#### Documentation
- `AGENTS.md`: Corrected RPC spec file path reference

[0.2.0]: https://github.com/nakhan98/transmission-qt-remote/compare/v0.1.0...v0.2.0

## [0.1.0] - 2025-12-01

Initial alpha release.

### Added
- Basic torrent viewing and monitoring
- Start/pause/verify torrent operations
- Connection settings with auto-connect
- Secure credential storage using platform keyrings
- Light/Dark theme support
- System tray integration
- Real-time search and filtering
- Comprehensive test suite (146 tests)
- IP2Location integration for country lookup

### Limitations
- Adding torrents not yet supported
- Deleting torrents not yet supported
- Advanced settings modification not available
- Bandwidth limit controls not implemented

[0.1.0]: https://github.com/nakhan98/transmission-qt-remote/releases/tag/v0.1.0
