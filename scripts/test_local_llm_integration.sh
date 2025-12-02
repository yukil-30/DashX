#!/bin/bash
#
# Integration tests for the local LLM service
#
# Usage:
#   ./tests/test_local_llm_integration.sh           # Run all tests
#   ./tests/test_local_llm_integration.sh --stub    # Run in stub mode (no model needed)
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - For real model tests: ./scripts/download_model.sh has been run
#
# Expected outputs are documented inline for each test.
#

set -e

# Configuration
LLM_PORT="${LOCAL_LLM_PORT:-8080}"
LLM_URL="http://localhost:${LLM_PORT}"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-dashx}"
STUB_MODE="${1:-}"
TIMEOUT=120  # seconds to wait for service

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "\n${YELLOW}[TEST]${NC} $1"
}

run_test() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if echo "$actual" | grep -q "$expected"; then
        log_info "✓ PASSED: $name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "✗ FAILED: $name"
        log_error "  Expected to contain: $expected"
        log_error "  Actual: $actual"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

cleanup() {
    log_info "Cleaning up..."
    docker compose --profile local-llm down local-llm 2>/dev/null || true
}

wait_for_health() {
    log_info "Waiting for local LLM service to be healthy (timeout: ${TIMEOUT}s)..."
    
    local elapsed=0
    local interval=5
    
    while [ $elapsed -lt $TIMEOUT ]; do
        if curl -s "${LLM_URL}/health" | grep -q '"status":"ok"'; then
            log_info "Service is healthy!"
            return 0
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        echo "  Waiting... (${elapsed}s/${TIMEOUT}s)"
    done
    
    log_error "Service did not become healthy within ${TIMEOUT}s"
    return 1
}

# =============================================================================
# Main Test Flow
# =============================================================================

echo "=============================================="
echo "Local LLM Integration Tests"
echo "=============================================="
echo ""

# Check prerequisites
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    log_error "curl is not installed"
    exit 1
fi

# Determine test mode
if [ "$STUB_MODE" = "--stub" ]; then
    log_info "Running in STUB mode (no model required)"
    export LOCAL_LLM_STUB_MODE=true
else
    log_info "Running in FULL mode (model required)"
    
    # Check if model exists
    if [ ! -f "./models/local-llm/model.gguf" ]; then
        log_warn "Model not found at ./models/local-llm/model.gguf"
        log_warn "Run ./scripts/download_model.sh first, or use --stub flag"
        log_info "Falling back to stub mode for tests..."
        export LOCAL_LLM_STUB_MODE=true
    fi
fi

# Set up trap for cleanup
trap cleanup EXIT

# =============================================================================
# Test 1: Start the service
# =============================================================================
log_test "Starting local-llm service"

log_info "Building and starting service..."
docker compose --profile local-llm up -d --build local-llm

# Wait for health
if ! wait_for_health; then
    log_error "Service failed to start"
    docker compose --profile local-llm logs local-llm
    exit 1
fi

run_test "Service started successfully" "ok" "ok"

# =============================================================================
# Test 2: Health endpoint
# =============================================================================
log_test "GET /health endpoint"

# Expected output:
# {
#   "status": "ok",
#   "model_loaded": true|false,
#   "stub_mode": true|false,
#   "model_path": "/models/model.gguf"|null,
#   "message": "..."
# }

HEALTH_RESPONSE=$(curl -s "${LLM_URL}/health")
echo "Response: $HEALTH_RESPONSE"

run_test "Health returns status ok" '"status":"ok"' "$HEALTH_RESPONSE"

# =============================================================================
# Test 3: Generate endpoint - simple prompt
# =============================================================================
log_test "POST /v1/generate - simple prompt"

# Request:
# {"prompt": "Hello, how are you?", "max_tokens": 32}
#
# Expected output:
# {
#   "text": "...",  // Non-empty string
#   "tokens_used": ...,
#   "model": "local-llm" or "stub-local-llm",
#   "latency_ms": ...
# }

GENERATE_RESPONSE=$(curl -s -X POST "${LLM_URL}/v1/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello, how are you?", "max_tokens": 32}')
echo "Response: $GENERATE_RESPONSE"

run_test "Generate returns text field" '"text":' "$GENERATE_RESPONSE"
run_test "Generate returns model field" '"model":' "$GENERATE_RESPONSE"

# Check that text is not empty
if echo "$GENERATE_RESPONSE" | grep -q '"text":""'; then
    log_error "✗ FAILED: Text field is empty"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    log_info "✓ PASSED: Text field is non-empty"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))

# =============================================================================
# Test 4: Generate endpoint - with parameters
# =============================================================================
log_test "POST /v1/generate - with temperature and max_tokens"

GENERATE_PARAMS=$(curl -s -X POST "${LLM_URL}/v1/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "What is 2+2?", "max_tokens": 16, "temperature": 0.1}')
echo "Response: $GENERATE_PARAMS"

run_test "Generate with params returns text" '"text":' "$GENERATE_PARAMS"

# =============================================================================
# Test 5: Root endpoint
# =============================================================================
log_test "GET / - root endpoint"

# Expected output:
# {
#   "service": "Local LLM Server",
#   "version": "1.0.0",
#   ...
# }

ROOT_RESPONSE=$(curl -s "${LLM_URL}/")
echo "Response: $ROOT_RESPONSE"

run_test "Root returns service name" '"service":"Local LLM Server"' "$ROOT_RESPONSE"

# =============================================================================
# Test 6: Models endpoint
# =============================================================================
log_test "GET /v1/models - list models"

MODELS_RESPONSE=$(curl -s "${LLM_URL}/v1/models")
echo "Response: $MODELS_RESPONSE"

run_test "Models returns data array" '"data":' "$MODELS_RESPONSE"

# =============================================================================
# Test 7: Invalid request handling
# =============================================================================
log_test "POST /v1/generate - invalid request (missing prompt)"

INVALID_RESPONSE=$(curl -s -X POST "${LLM_URL}/v1/generate" \
    -H "Content-Type: application/json" \
    -d '{"max_tokens": 32}')
echo "Response: $INVALID_RESPONSE"

# Should return validation error
run_test "Invalid request returns error" 'detail' "$INVALID_RESPONSE"

# =============================================================================
# Test Summary
# =============================================================================
echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo "Tests run:    $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    log_info "All tests passed! ✓"
    exit 0
else
    log_error "Some tests failed!"
    exit 1
fi
