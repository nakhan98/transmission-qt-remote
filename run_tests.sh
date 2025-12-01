#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Use podman by default, but allow override via environment variable
CONTAINER_RUNTIME=${CONTAINER_RUNTIME:-podman}

echo -e "${YELLOW}Running unit tests using ${CONTAINER_RUNTIME} (no GUI dependencies)...${NC}"
$CONTAINER_RUNTIME build -f Dockerfile.unit -t transmission-qt-test-unit .
$CONTAINER_RUNTIME run --rm transmission-qt-test-unit
echo -e "${GREEN}Unit tests completed successfully!${NC}\n"

# Check if we should run integration tests (default yes)
RUN_INTEGRATION=${1:-yes}
if [ "$RUN_INTEGRATION" != "no" ]; then
    echo -e "${YELLOW}Building and running integration tests with ${CONTAINER_RUNTIME} (with GUI dependencies)...${NC}"
    echo -e "${YELLOW}Note: This may take longer due to QT and X11 dependencies${NC}"
    $CONTAINER_RUNTIME build -f Dockerfile.integration -t transmission-qt-test-integration .
    $CONTAINER_RUNTIME run --rm transmission-qt-test-integration
    echo -e "${GREEN}Integration tests completed successfully!${NC}"
else
    echo -e "${YELLOW}Skipping integration tests${NC}"
fi

echo -e "\n${GREEN}All tests completed!${NC}"