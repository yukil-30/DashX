#!/bin/bash
#
# DashX Verification Test Runner
# Orchestrates docker-compose setup, runs pytest suite, and reports results
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
TEST_DIR="$PROJECT_ROOT/tests/verification"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Options
RUN_MOCK_SERVICES=true
TEARDOWN_AFTER=false
VERBOSE=false
SPECIFIC_TEST=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --teardown)
            TEARDOWN_AFTER=true
            shift
            ;;
        --no-mocks)
            RUN_MOCK_SERVICES=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --teardown        Tear down services after tests"
            echo "  --no-mocks        Don't use mock services"
            echo "  --verbose, -v     Verbose pytest output"
            echo "  --test <name>     Run specific test file"
            echo "  --help, -h        Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Print header
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║         DashX Verification Test Suite                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7] Checking Prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found. Installing...${NC}"
    cd "$BACKEND_DIR" && pip install pytest pytest-asyncio httpx asyncpg
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"

# Step 2: Start Docker services
echo -e "\n${YELLOW}[2/7] Starting Docker Services...${NC}"

cd "$PROJECT_ROOT"

# Start core services
echo "Starting postgres, backend..."
docker-compose up -d postgres backend

# Wait for postgres
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U restaurant_user &> /dev/null; then
        break
    fi
    sleep 1
done

# Wait for backend
echo "Waiting for backend API..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        break
    fi
    sleep 1
done

echo -e "${GREEN}✓ Core services running${NC}"

# Step 2.5: Run database migrations
echo -e "\n${YELLOW}[2.5/7] Running Database Migrations...${NC}"

cd "$BACKEND_DIR"
docker-compose exec -T backend alembic upgrade head

echo -e "${GREEN}✓ Migrations applied${NC}"

# Step 3: Start mock services if needed
if [ "$RUN_MOCK_SERVICES" = true ]; then
    echo -e "\n${YELLOW}[3/7] Starting Mock Services...${NC}"
    
    # Start mock LLM
    cd "$BACKEND_DIR/tests/mock_adapters"
    nohup python mock_llm_server.py > /tmp/mock_llm.log 2>&1 &
    MOCK_LLM_PID=$!
    
    # Start mock STT
    nohup python mock_stt_server.py > /tmp/mock_stt.log 2>&1 &
    MOCK_STT_PID=$!
    
    # Start mock NLP
    nohup python mock_nlp_server.py > /tmp/mock_nlp.log 2>&1 &
    MOCK_NLP_PID=$!
    
    # Wait for mocks to start
    sleep 3
    
    echo -e "${GREEN}✓ Mock services running (LLM:8001, STT:8002, NLP:8003)${NC}"
else
    echo -e "\n${YELLOW}[3/7] Skipping Mock Services (using real services)${NC}"
fi

# Step 4: Load seed data
echo -e "\n${YELLOW}[4/7] Loading Seed Data...${NC}"

docker-compose exec -T postgres psql -U restaurant_user -d restaurant_db < "$TEST_DIR/fixtures/seed_full_stack.sql"

echo -e "${GREEN}✓ Seed data loaded${NC}"

# Step 5: Run health checks
echo -e "\n${YELLOW}[5/7] Running Health Checks...${NC}"

# Check backend
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Backend health check failed${NC}"
    exit 1
fi

# Check database
if ! docker-compose exec -T postgres psql -U restaurant_user -d restaurant_db -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}✗ Database health check failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Health checks passed${NC}"

# Step 6: Run pytest
echo -e "\n${YELLOW}[6/7] Running Test Suite...${NC}"
echo ""

cd "$TEST_DIR"

# Build pytest command
PYTEST_CMD="pytest"
PYTEST_ARGS="-v --tb=short"

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -s"
fi

if [ -n "$SPECIFIC_TEST" ]; then
    PYTEST_ARGS="$PYTEST_ARGS $SPECIFIC_TEST"
fi

# Set environment variables
export DATABASE_URL="postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db"
export BACKEND_URL="http://localhost:8000"
export USE_MOCK_LLM=true
export USE_MOCK_STT=true
export USE_MOCK_NLP=true

# Run tests
set +e  # Don't exit on test failure
$PYTEST_CMD $PYTEST_ARGS
TEST_EXIT_CODE=$?
set -e

# Step 7: Cleanup
echo -e "\n${YELLOW}[7/7] Cleanup...${NC}"

if [ "$RUN_MOCK_SERVICES" = true ]; then
    # Kill mock services
    if [ -n "$MOCK_LLM_PID" ]; then kill $MOCK_LLM_PID 2>/dev/null || true; fi
    if [ -n "$MOCK_STT_PID" ]; then kill $MOCK_STT_PID 2>/dev/null || true; fi
    if [ -n "$MOCK_NLP_PID" ]; then kill $MOCK_NLP_PID 2>/dev/null || true; fi
    echo "✓ Mock services stopped"
fi

if [ "$TEARDOWN_AFTER" = true ]; then
    cd "$PROJECT_ROOT"
    docker-compose down
    echo "✓ Docker services stopped"
fi

# Print summary
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}║                  ✓✓✓ ALL TESTS PASSED ✓✓✓                          ║${NC}"
else
    echo -e "${RED}║                  ✗✗✗ SOME TESTS FAILED ✗✗✗                        ║${NC}"
fi
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

exit $TEST_EXIT_CODE
