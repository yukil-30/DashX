#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🍽️  Starting Local AI-enabled Restaurant...${NC}"

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
fi

# Stop any existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true

# Build and start all services
echo -e "${GREEN}Building and starting services...${NC}"
docker-compose up --build -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for postgres
echo -n "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U restaurant_user -d restaurant_db > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}Ready!${NC}"

# Wait for backend
echo -n "Waiting for Backend..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}Ready!${NC}"

# Wait for frontend
echo -n "Waiting for Frontend..."
until curl -s http://localhost:3000 > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}Ready!${NC}"

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose exec -T backend python -c "from app.database import init_db; init_db()" 2>/dev/null || echo -e "${YELLOW}Migrations skipped (will be implemented later)${NC}"

# Seed minimal data
echo -e "${YELLOW}Seeding initial data...${NC}"
docker-compose exec -T backend python -c "from app.seed import seed_data; seed_data()" 2>/dev/null || echo -e "${YELLOW}Seeding skipped (will be implemented later)${NC}"

echo -e ""
echo -e "${GREEN}✅ All services are running!${NC}"
echo -e ""
echo -e "📍 Service URLs:"
echo -e "   Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "   Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "   LLM Stub:  ${GREEN}http://localhost:8001${NC}"
echo -e "   PostgreSQL: localhost:5432"
echo -e ""
echo -e "📝 Useful commands:"
echo -e "   View logs:     ${YELLOW}docker-compose logs -f${NC}"
echo -e "   Stop services: ${YELLOW}docker-compose down${NC}"
echo -e "   Run tests:     ${YELLOW}./run-tests.sh${NC}"
