#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timeout settings
MAX_WAIT=120
POLL_INTERVAL=2

echo -e "${GREEN}🍽️  Starting Local AI-enabled Restaurant...${NC}"
echo -e ""

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ Error: $1 is not installed${NC}"
        echo -e "   Please install $1 and try again"
        exit 1
    fi
}

# Function to wait for service
wait_for_service() {
    local name=$1
    local url=$2
    local wait_time=0
    
    echo -n "Waiting for $name..."
    while ! curl -s "$url" > /dev/null 2>&1; do
        if [ $wait_time -ge $MAX_WAIT ]; then
            echo -e " ${RED}TIMEOUT${NC}"
            echo -e "${RED}❌ $name did not start within ${MAX_WAIT}s${NC}"
            echo -e "${YELLOW}   Check logs with: docker-compose logs $name${NC}"
            return 1
        fi
        echo -n "."
        sleep $POLL_INTERVAL
        wait_time=$((wait_time + POLL_INTERVAL))
    done
    echo -e " ${GREEN}Ready! (${wait_time}s)${NC}"
    return 0
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"
check_command docker
check_command docker-compose
check_command curl

# Check if Docker daemon is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    echo -e "   Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✅ Prerequisites satisfied${NC}"
echo -e ""

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
fi

# Stop any existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true

# Build and start all services
echo -e ""
echo -e "${GREEN}Building and starting services...${NC}"
echo -e "${BLUE}   This may take a few minutes on first run...${NC}"
docker-compose up --build -d

# Wait for services to be healthy
echo -e ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for postgres (check via docker-compose exec)
echo -n "Waiting for PostgreSQL..."
wait_time=0
until docker-compose exec -T postgres pg_isready -U restaurant_user -d restaurant_db > /dev/null 2>&1; do
    if [ $wait_time -ge $MAX_WAIT ]; then
        echo -e " ${RED}TIMEOUT${NC}"
        echo -e "${RED}❌ PostgreSQL did not start within ${MAX_WAIT}s${NC}"
        echo -e "${YELLOW}   Check logs with: docker-compose logs postgres${NC}"
        exit 1
    fi
    echo -n "."
    sleep $POLL_INTERVAL
    wait_time=$((wait_time + POLL_INTERVAL))
done
echo -e " ${GREEN}Ready! (${wait_time}s)${NC}"

# Wait for other services
wait_for_service "Backend" "http://localhost:8000/health" || exit 1
wait_for_service "Frontend" "http://localhost:3000" || exit 1
wait_for_service "LLM Stub" "http://localhost:8001/health" || exit 1

# Run migrations
echo -e ""
echo -e "${YELLOW}Running database migrations...${NC}"
if docker-compose exec -T backend python -c "from app.database import init_db; init_db()" 2>/dev/null; then
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Migrations skipped (tables may already exist or models not defined yet)${NC}"
fi

# Seed minimal data
echo -e ""
echo -e "${YELLOW}Seeding initial data...${NC}"
if docker-compose exec -T backend python -c "from app.seed import seed_data; seed_data()" 2>/dev/null; then
    echo -e "${GREEN}✅ Data seeded${NC}"
else
    echo -e "${YELLOW}⚠️  Seeding skipped (will be implemented with database models)${NC}"
fi

echo -e ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All services are running!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e ""
echo -e "📍 ${BLUE}Service URLs:${NC}"
echo -e "   Frontend:   ${GREEN}http://localhost:3000${NC}"
echo -e "   Backend:    ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs:   ${GREEN}http://localhost:8000/docs${NC}"
echo -e "   LLM Stub:   ${GREEN}http://localhost:8001${NC}"
echo -e "   PostgreSQL: localhost:5432"
echo -e ""
echo -e "📝 ${BLUE}Useful commands:${NC}"
echo -e "   View logs:      ${YELLOW}docker-compose logs -f${NC}"
echo -e "   Stop services:  ${YELLOW}docker-compose down${NC}"
echo -e "   Run tests:      ${YELLOW}./run-tests.sh${NC}"
echo -e "   Backend shell:  ${YELLOW}docker-compose exec backend bash${NC}"
echo -e "   DB shell:       ${YELLOW}docker-compose exec postgres psql -U restaurant_user -d restaurant_db${NC}"
echo -e ""
