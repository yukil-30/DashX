# DashX - Local AI-enabled Restaurant

Final Project for Software Engineering (E-Restaurant App)

**Authors:**
- Joseph Helfenbein
- Bryant Dong
- Yuki Li
- Jacob Li

---

## 🍽️ Overview

DashX is a full-stack AI-enabled restaurant management system that runs entirely locally. It features:

- **AI-Powered Menu Recommendations** - Get personalized dish suggestions based on preferences
- **Natural Language Ordering** - Order using conversational AI
- **Real-time Kitchen Dashboard** - Track orders and kitchen status
- **Smart Inventory Management** - AI-assisted stock predictions

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| Local LLM | Ollama/HuggingFace (stub for development) |
| Container | Docker Compose |

## 📁 Project Structure

```
DashX/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py       # Main FastAPI application
│   │   ├── database.py   # Database configuration
│   │   └── seed.py       # Data seeding script
│   ├── migrations/       # Alembic database migrations
│   │   ├── env.py        # Alembic environment config
│   │   └── versions/     # Migration scripts
│   │       ├── 20251130_001_initial_schema.py
│   │       └── 20251130_002_add_indices.py
│   ├── sql/              # SQL scripts
│   │   ├── seed_data.sql # Demo data for testing
│   │   └── smoke_tests.sql # Schema verification
│   ├── tests/
│   │   ├── test_health.py
│   │   └── test_schema.py # Schema integrity tests
│   ├── schema_documentation.md  # ER diagrams and design docs
│   ├── alembic.ini       # Alembic configuration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── test/
│   ├── Dockerfile
│   └── package.json
├── llm-stub/             # Local LLM stub service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml    # Docker Compose configuration
├── run-local.sh          # Quick start script
├── run-tests.sh          # Test runner script
└── .env.example          # Environment variables template
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone and Setup

```bash
git clone https://github.com/yukil-30/DashX.git
cd DashX
cp .env.example .env
```

### 2. Start All Services

**Option A: Using the quick start script**
```bash
chmod +x run-local.sh
./run-local.sh
```

**Option B: Using Docker Compose directly**
```bash
docker-compose up --build
```

### 3. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| LLM Stub | http://localhost:8001 |

## 🧪 Running Tests

### Run All Tests
```bash
chmod +x run-tests.sh
./run-tests.sh
```

### Backend Tests (pytest)
```bash
docker-compose exec backend pytest -v
```

**Expected output:**
```
tests/test_health.py::TestHealthEndpoint::test_health_returns_200 PASSED
tests/test_health.py::TestHealthEndpoint::test_health_returns_ok_status PASSED
tests/test_health.py::TestHealthEndpoint::test_health_response_structure PASSED
tests/test_health.py::TestHealthEndpoint::test_health_version_present PASSED
tests/test_health.py::TestRootEndpoint::test_root_returns_200 PASSED
tests/test_health.py::TestRootEndpoint::test_root_returns_welcome_message PASSED
tests/test_health.py::TestRootEndpoint::test_root_includes_docs_link PASSED
```

### Frontend Tests (Vitest)
```bash
docker-compose exec frontend npm test
```

### Smoke Tests

**Backend Health Check:**
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{"status":"ok","version":"0.1.0","database":"connected","llm_stub":"connected"}
```

**Frontend Smoke Test:**
```bash
curl -s http://localhost:3000 | grep -o "<title>.*</title>"
```
Expected response:
```
<title>Local AI Restaurant</title>
```

**LLM Stub Health Check:**
```bash
curl http://localhost:8001/health
```
Expected response:
```json
{"status":"ok","model":"stub-llm-v1","message":"LLM Stub service is running. Replace with Ollama/HF for production."}
```

## 🛠️ Development

### Stopping Services
```bash
docker-compose down
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Rebuilding After Changes
```bash
docker-compose up --build
```

### Database Access
```bash
docker-compose exec postgres psql -U restaurant_user -d restaurant_db
```

## 📝 API Endpoints

### Health & Status
- `GET /health` - Health check with dependency status
- `GET /` - API information

### Menu (Coming Soon)
- `GET /api/menu` - List menu items
- `POST /api/menu` - Add menu item
- `GET /api/menu/{id}` - Get menu item details

### Orders (Coming Soon)
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order status
- `PUT /api/orders/{id}` - Update order

### AI Features (Coming Soon)
- `POST /api/ai/recommend` - Get menu recommendations
- `POST /api/ai/chat` - Natural language interaction

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database user | `restaurant_user` |
| `POSTGRES_PASSWORD` | Database password | `restaurant_password` |
| `POSTGRES_DB` | Database name | `restaurant_db` |
| `DATABASE_URL` | Full database connection URL | auto-constructed |
| `VITE_API_URL` | Backend API URL for frontend | `http://localhost:8000` |
| `LLM_STUB_URL` | LLM service URL | `http://llm-stub:8001` |
| `DEBUG` | Enable debug mode | `true` |

## 📊 Expected Service Logs

When running `docker-compose up --build`, you should see:

**PostgreSQL Ready:**
```
restaurant_postgres  | PostgreSQL init process complete; ready for start up.
restaurant_postgres  | LOG:  database system is ready to accept connections
```

**Backend Ready:**
```
restaurant_backend   | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
restaurant_backend   | INFO:     Started reloader process
```

**Frontend Ready:**
```
restaurant_frontend  | VITE v5.0.8  ready in XXX ms
restaurant_frontend  |   ➜  Local:   http://localhost:3000/
```

**LLM Stub Ready:**
```
restaurant_llm_stub  | INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

## 🗄️ Database Migrations

The database schema is managed using Alembic migrations. All migrations are located in `backend/migrations/versions/`.

### Migration Files

| Migration | Description |
|-----------|-------------|
| `001_initial_schema` | Creates all core tables (accounts, dishes, orders, etc.) with constraints and triggers |
| `002_add_indices` | Adds performance indices for common query patterns |

### Applying Migrations

**Option A: Using Docker Compose (Recommended)**
```bash
# Start services first
docker-compose up -d postgres

# Apply all migrations
docker-compose exec backend alembic upgrade head

# Load seed data
docker-compose exec postgres psql -U restaurant_user -d restaurant_db -f /app/sql/seed_data.sql
```

**Option B: Local Development**
```bash
cd backend

# Apply all migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 001_initial_schema
alembic upgrade 002_add_indices

# Load seed data
psql -U restaurant_user -d restaurant_db -f sql/seed_data.sql
```

### Rollback Migrations
```bash
# Rollback one step
docker-compose exec backend alembic downgrade -1

# Rollback to base (removes all tables)
docker-compose exec backend alembic downgrade base
```

### Verify Schema

**Check tables exist:**
```bash
docker-compose exec postgres psql -U restaurant_user -d restaurant_db -c "\dt"
```

**Run smoke tests:**
```bash
docker-compose exec postgres psql -U restaurant_user -d restaurant_db -f /app/sql/smoke_tests.sql
```

**Run pytest schema tests:**
```bash
docker-compose exec backend pytest tests/test_schema.py -v
```

### Seed Data Contents

The seed data (`sql/seed_data.sql`) includes:
- 1 Restaurant (DashX Bistro)
- 11 Accounts: 1 manager, 2 chefs, 2 delivery persons, 5 customers (1 VIP), 1 visitor
- 5 Dishes with pricing and ratings
- 5 Orders demonstrating various statuses
- 6 Delivery bids
- Sample complaints, transactions, and forum posts

**Test account credentials** (all use password: `password123`):
| Email | Role | Balance |
|-------|------|---------|
| `manager@dashxbistro.com` | Manager | $5,000 |
| `vip.john@example.com` | VIP Customer | $1,000 |
| `customer.alice@example.com` | Customer | $1.50 (for failure tests) |

### Sample Queries

**Top 5 most popular dishes:**
```sql
SELECT d.name, COALESCE(SUM(od.quantity), 0) as order_count
FROM dishes d
LEFT JOIN ordered_dishes od ON d.id = od.dish_id
GROUP BY d.id
ORDER BY order_count DESC
LIMIT 5;
```

**Top 5 highest-rated dishes:**
```sql
SELECT name, average_rating, review_count
FROM dishes
ORDER BY average_rating DESC, review_count DESC
LIMIT 5;
```

**Customer order history:**
```sql
SELECT o.id, o.status, o.final_cost/100.0 as total, o.order_datetime
FROM orders o
WHERE o.account_id = 6  -- VIP John
ORDER BY o.order_datetime DESC;
```

---

## 🔄 Roadmap

- [x] Project skeleton with Docker Compose
- [x] Backend FastAPI with health check
- [x] Frontend React + TypeScript
- [x] LLM Stub service
- [x] Database models and migrations
- [ ] Menu management API
- [ ] Order management API
- [ ] AI recommendation integration
- [ ] Replace LLM stub with Ollama
- [ ] Kitchen dashboard UI
- [ ] Real-time order updates (WebSocket)

## ❓ Troubleshooting

### Docker Issues

**"Cannot connect to Docker daemon"**
```bash
# Make sure Docker Desktop is running
# On macOS: open Docker Desktop from Applications
# On Linux: sudo systemctl start docker
```

**"Port already in use"**
```bash
# Find what's using the port
lsof -i :8000  # for backend
lsof -i :3000  # for frontend
lsof -i :5432  # for postgres

# Kill the process or change ports in docker-compose.yml
```

**"Build failed"**
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Service Not Starting

**Backend won't start**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: wait a few seconds and try again
# - Import error: check requirements.txt is correct
```

**Frontend shows blank page**
```bash
# Check if API URL is correct
# In browser console, check for CORS errors
# Verify VITE_API_URL in .env matches your setup
```

**Database connection failed**
```bash
# Check if postgres is running
docker-compose ps postgres

# Connect manually to verify
docker-compose exec postgres psql -U restaurant_user -d restaurant_db

# Reset database
docker-compose down -v  # Warning: deletes all data
docker-compose up
```

### Test Failures

**"Container not running" errors**
```bash
# Start services first
./run-local.sh

# Then run tests
./run-tests.sh
```

**Frontend tests fail**
```bash
# Install dependencies inside container
docker-compose exec frontend npm install
docker-compose exec frontend npm test
```

### Common Solutions

1. **Full reset**: `docker-compose down -v && docker-compose up --build`
2. **Check logs**: `docker-compose logs -f [service_name]`
3. **Restart single service**: `docker-compose restart backend`
4. **Rebuild single service**: `docker-compose up --build backend`

## 📄 License

This project is for educational purposes as part of a Software Engineering course.
