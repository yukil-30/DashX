#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Running Tests for Local AI-enabled Restaurant...${NC}"
echo -e ""

# Backend Tests
echo -e "${YELLOW}=== Backend Tests ===${NC}"
echo -e "Running pytest in backend container..."
docker-compose exec -T backend pytest -v --tb=short 2>/dev/null || {
    echo -e "${RED}Backend tests failed or container not running.${NC}"
    echo -e "${YELLOW}Try running: docker-compose up -d first${NC}"
}

echo -e ""

# Frontend Smoke Test
echo -e "${YELLOW}=== Frontend Smoke Test ===${NC}"
echo -e "Checking if frontend serves index page..."
if curl -s http://localhost:3000 | grep -q "html"; then
    echo -e "${GREEN}✅ Frontend is serving HTML content${NC}"
else
    echo -e "${RED}❌ Frontend smoke test failed${NC}"
fi

echo -e ""

# Backend Health Check
echo -e "${YELLOW}=== Backend Health Check ===${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ Backend health check passed: $HEALTH_RESPONSE${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo -e "Response: $HEALTH_RESPONSE"
fi

echo -e ""

# LLM Stub Health Check
echo -e "${YELLOW}=== LLM Stub Health Check ===${NC}"
LLM_RESPONSE=$(curl -s http://localhost:8001/health)
if echo "$LLM_RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ LLM Stub health check passed: $LLM_RESPONSE${NC}"
else
    echo -e "${RED}❌ LLM Stub health check failed${NC}"
    echo -e "Response: $LLM_RESPONSE"
fi

echo -e ""
echo -e "${GREEN}🎉 Test run complete!${NC}"
