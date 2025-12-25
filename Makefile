# Determine OS and architecture for virtual environment name
OS := $(shell uname -s)
ARCH := $(shell uname -m)
VENV_DIR := .venv.$(OS)_$(ARCH)
PYTHON := $(VENV_DIR)/bin/python
VENV_BIN := $(VENV_DIR)/bin
UV := $(shell command -v uv >/dev/null 2>&1 && printf uv)

# Container runtime - can be overridden with environment variable or make argument
# e.g., make docker_test CONTAINER_RUNTIME=podman
CONTAINER_RUNTIME ?= podman

.PHONY: setup_venv install run test test_unit test_integration container_build_unit container_build_integration container_build container_test_unit container_test_integration container_test clean clean_all coverage download_geoip check_geoip

setup_venv:
	@echo "Creating virtual environment for $(OS) $(ARCH)..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "$(VENV_DIR) already exists"; \
	elif [ -n "$(UV)" ]; then \
		if $(UV) venv --seed --python 3.12 "$(VENV_DIR)"; then \
			:; \
		else \
			echo "uv venv failed, falling back to python3"; \
			python3 -m venv "$(VENV_DIR)"; \
		fi; \
	else \
		python3 -m venv "$(VENV_DIR)"; \
	fi

install: setup_venv
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

run: check_geoip
	@echo "Starting Transmission Qt Remote GUI..."
	$(VENV_BIN)/transmission-qt-remote

# Check if GeoIP database exists and download if not
check_geoip:
	@if [ ! -f IP2LOCATION-LITE-DB1.BIN ]; then \
		echo "IP2Location database not found. Downloading now..."; \
		$(MAKE) download_geoip; \
	else \
		echo "IP2Location database found."; \
	fi

# Run all tests
test:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest -v

# Run only unit tests
test_unit:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest tests/unit/ -v

# Run only integration tests (use offscreen platform like Docker)
test_integration:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest tests/integration/ -v

# Build targets
container_build_unit:
	$(CONTAINER_RUNTIME) build -f Dockerfile.unit -t transmission-qt-test-unit .

container_build_integration: container_build_unit
	$(CONTAINER_RUNTIME) build -f Dockerfile.integration -t transmission-qt-test-integration .

container_build: container_build_integration

# Test targets (depend on builds)
container_test_unit: container_build_unit
	$(CONTAINER_RUNTIME) run --rm transmission-qt-test-unit

# Run integration tests in container (with QT dependencies)
container_test_integration: container_build_integration
	$(CONTAINER_RUNTIME) run --rm transmission-qt-test-integration

# Run all tests in container
container_test:
	CONTAINER_RUNTIME="$(CONTAINER_RUNTIME)" ./run_tests.sh

# Aliases for backward compatibility
docker_test_unit: container_test_unit
docker_test_integration: container_test_integration
docker_test: container_test

# Clean current platform's virtual environment
clean:
	@echo "Cleaning temporary files and $(VENV_DIR)..."
	find ./ -name "*~" | xargs rm -fv || true
	rm -rf $(VENV_DIR)
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf .coverage

# Clean all virtual environments and temporary files across platforms
clean_all:
	@echo "Cleaning all virtual environments and temporary files..."
	find ./ -name "*~" | xargs rm -fv || true
	rm -rf .venv*
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf .coverage
	@echo "All virtual environments removed."

coverage:
	$(PYTHON) -m pytest --cov=transmission_client --cov-report=term-missing

# Download the latest IP2Location LITE database (DB1.LITE.BIN)
download_geoip:
	@echo "Downloading IP2Location LITE database..."
	@curl -L -o IP2LOCATION-LITE-DB1.BIN.ZIP "https://download.ip2location.com/lite/IP2LOCATION-LITE-DB1.BIN.ZIP"
	@echo "Extracting database file..."
	@unzip -o IP2LOCATION-LITE-DB1.BIN.ZIP IP2LOCATION-LITE-DB1.BIN
	@rm IP2LOCATION-LITE-DB1.BIN.ZIP
	@echo "IP2Location database downloaded successfully to IP2LOCATION-LITE-DB1.BIN"

# Provide information about current environment
info:
	@echo "OS: $(OS)"
	@echo "Architecture: $(ARCH)"
	@echo "Virtual environment: $(VENV_DIR)"
	@echo "Container runtime: $(CONTAINER_RUNTIME)"

lint:
	@echo "Running ruff check..."
	$(PYTHON) -m ruff check .
	@echo "Running ruff format..."
	$(PYTHON) -m ruff format .

typecheck:
	@echo "Running pyright type checking..."
	$(PYTHON) -m pyright --project pyrightconfig.json

