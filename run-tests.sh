#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${GREEN}🧪 Running Tests for Local AI-enabled Restaurant...${NC}"
echo -e ""

# Function to check if a service is running
check_service() {
    local name=$1
    local url=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to run a test and track results
run_test() {
    local test_name=$1
    local test_result=$2
    
    if [ $test_result -eq 0 ]; then
        echo -e "   ${GREEN}✅ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "   ${RED}❌ FAIL${NC}: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Check if services are running
echo -e "${BLUE}Checking service availability...${NC}"
SERVICES_RUNNING=true

if ! check_service "Backend" "http://localhost:8000/health"; then
    echo -e "${RED}❌ Backend is not running at http://localhost:8000${NC}"
    SERVICES_RUNNING=false
fi

if ! check_service "Frontend" "http://localhost:3000"; then
    echo -e "${RED}❌ Frontend is not running at http://localhost:3000${NC}"
    SERVICES_RUNNING=false
fi

if ! check_service "LLM Stub" "http://localhost:8001/health"; then
    echo -e "${RED}❌ LLM Stub is not running at http://localhost:8001${NC}"
    SERVICES_RUNNING=false
fi

if [ "$SERVICES_RUNNING" = false ]; then
    echo -e ""
    echo -e "${YELLOW}⚠️  Some services are not running.${NC}"
    echo -e "${YELLOW}   Start services with: ./run-local.sh${NC}"
    echo -e ""
    echo -e "${BLUE}Attempting to run available tests anyway...${NC}"
fi

echo -e ""

# Backend Unit Tests
echo -e "${YELLOW}=== Backend Unit Tests ===${NC}"
if docker-compose exec -T backend pytest -v --tb=short 2>&1; then
    echo -e "${GREEN}✅ Backend pytest suite passed${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    if docker-compose ps backend 2>/dev/null | grep -q "Up"; then
        echo -e "${RED}❌ Backend pytest suite failed${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    else
        echo -e "${YELLOW}⚠️  Backend container not running, skipping pytest${NC}"
    fi
fi

echo -e ""

# Backend Health Check
echo -e "${YELLOW}=== Backend Health Check ===${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null || echo "CONNECTION_FAILED")

if [ "$HEALTH_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo -e "   ${RED}❌ FAIL${NC}: Could not connect to backend"
    TESTS_FAILED=$((TESTS_FAILED + 1))
elif echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "   ${GREEN}✅ PASS${NC}: Backend returns status:ok"
    echo -e "   Response: $HEALTH_RESPONSE"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "   ${RED}❌ FAIL${NC}: Backend health check failed"
    echo -e "   Response: $HEALTH_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo -e ""

# Frontend Smoke Test
echo -e "${YELLOW}=== Frontend Smoke Test ===${NC}"
FRONTEND_RESPONSE=$(curl -s http://localhost:3000 2>/dev/null || echo "CONNECTION_FAILED")

if [ "$FRONTEND_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo -e "   ${RED}❌ FAIL${NC}: Could not connect to frontend"
    TESTS_FAILED=$((TESTS_FAILED + 1))
elif echo "$FRONTEND_RESPONSE" | grep -q "html"; then
    echo -e "   ${GREEN}✅ PASS${NC}: Frontend is serving HTML content"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    # Additional check for title
    if echo "$FRONTEND_RESPONSE" | grep -q "Local AI Restaurant"; then
        echo -e "   ${GREEN}✅ PASS${NC}: Frontend has correct title"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "   ${YELLOW}⚠️  WARN${NC}: Title tag not found (may need page render)"
    fi
else
    echo -e "   ${RED}❌ FAIL${NC}: Frontend did not return HTML"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo -e ""

# LLM Stub Health Check
echo -e "${YELLOW}=== LLM Stub Health Check ===${NC}"
LLM_RESPONSE=$(curl -s http://localhost:8001/health 2>/dev/null || echo "CONNECTION_FAILED")

if [ "$LLM_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo -e "   ${RED}❌ FAIL${NC}: Could not connect to LLM Stub"
    TESTS_FAILED=$((TESTS_FAILED + 1))
elif echo "$LLM_RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "   ${GREEN}✅ PASS${NC}: LLM Stub returns status:ok"
    echo -e "   Response: $LLM_RESPONSE"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "   ${RED}❌ FAIL${NC}: LLM Stub health check failed"
    echo -e "   Response: $LLM_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo -e ""

# LLM Stub Chat Test
echo -e "${YELLOW}=== LLM Stub Chat Endpoint Test ===${NC}"
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8001/chat \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"What do you recommend?"}]}' 2>/dev/null || echo "CONNECTION_FAILED")

if [ "$CHAT_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo -e "   ${RED}❌ FAIL${NC}: Could not connect to LLM Stub"
    TESTS_FAILED=$((TESTS_FAILED + 1))
elif echo "$CHAT_RESPONSE" | grep -q '"response"'; then
    echo -e "   ${GREEN}✅ PASS${NC}: LLM Stub returns chat response"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "   ${RED}❌ FAIL${NC}: LLM Stub chat endpoint failed"
    echo -e "   Response: $CHAT_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo -e ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                       TEST SUMMARY                          ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e ""
echo -e "   ${GREEN}Passed${NC}: $TESTS_PASSED"
echo -e "   ${RED}Failed${NC}: $TESTS_FAILED"
echo -e "   Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo -e ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check output above for details.${NC}"
    exit 1
fi
