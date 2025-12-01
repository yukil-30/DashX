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

### Authentication

#### Register a New User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser@example.com",
    "password": "SecureP@ss123",
    "display_name": "John Doe",
    "email": "newuser@example.com",
    "role_requested": "customer"
  }'
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Validation Rules:**
- `password`: Minimum 8 characters, must contain at least one letter and one digit
- `role_requested`: Only `customer` or `visitor` (employee roles require manager approval)

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser@example.com",
    "password": "SecureP@ss123"
  }'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials"
}
```

#### Get Current User Profile
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "newuser@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "account_type": "customer",
    "balance_cents": 0,
    "warnings": 0,
    "is_blacklisted": false,
    "free_delivery_credits": 0,
    "created_at": "2025-12-01T10:30:00Z",
    "last_login_at": "2025-12-01T10:30:00Z"
  }
}
```

#### Logout
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out",
  "detail": "Please delete the access token on your client"
}
```

### Account Management

#### Get Account Balance
```bash
curl http://localhost:8000/account/balance \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "balance_cents": 5000,
  "balance_formatted": "$50.00"
}
```

#### Deposit Funds
```bash
curl -X POST http://localhost:8000/account/deposit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"amount_cents": 5000}'
```

**Response (200 OK):**
```json
{
  "message": "Deposit successful",
  "new_balance_cents": 5000,
  "new_balance_formatted": "$50.00",
  "transaction_id": 1
}
```

**Error Response (422 Validation Error):**
```json
{
  "detail": [
    {
      "loc": ["body", "amount_cents"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

### Role-Based Access Control

The API uses JWT-based authentication with role-based access control:

| Role | Description | Self-Register |
|------|-------------|---------------|
| `visitor` | Browse-only access | ✅ Yes |
| `customer` | Can place orders, deposit funds | ✅ Yes |
| `vip` | Premium customer with perks | ❌ Upgraded by manager |
| `chef` | Kitchen staff, can manage dishes | ❌ Manager approval required |
| `delivery` | Delivery personnel | ❌ Manager approval required |
| `manager` | Full system access | ❌ Manager approval required |

### Dishes API

#### List Dishes (with Search & Filtering)
```bash
# List all dishes (paginated)
curl "http://localhost:8000/dishes?page=1&per_page=20"

# Search by name
curl "http://localhost:8000/dishes?q=pasta"

# Filter by chef
curl "http://localhost:8000/dishes?chef_id=2"

# Sort by popularity, rating, price, or newest
curl "http://localhost:8000/dishes?order_by=popular"
curl "http://localhost:8000/dishes?order_by=rating"
curl "http://localhost:8000/dishes?order_by=price"
```

**Response (200 OK):**
```json
{
  "dishes": [
    {
      "id": 1,
      "name": "Spaghetti Carbonara",
      "description": "Classic Italian pasta with eggs, cheese, and pancetta",
      "price_cents": 1499,
      "price_formatted": "$14.99",
      "category": "main",
      "is_available": true,
      "is_special": false,
      "average_rating": 4.5,
      "review_count": 28,
      "order_count": 156,
      "chef_id": 2,
      "chef_name": "Chef Antonio",
      "images": [
        {"id": 1, "image_url": "/static/images/carbonara.jpg", "display_order": 0}
      ],
      "picture": "/static/images/carbonara.jpg",
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-01T10:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 20,
  "total_pages": 2
}
```

#### Get Single Dish
```bash
curl http://localhost:8000/dishes/1
```

#### Create Dish (Chef/Manager Only)
```bash
curl -X POST http://localhost:8000/dishes \
  -H "Authorization: Bearer YOUR_CHEF_TOKEN" \
  -F "name=New Signature Dish" \
  -F "description=A delicious new creation" \
  -F "price_cents=1899" \
  -F "category=main" \
  -F "is_available=true" \
  -F "images=@/path/to/image1.jpg" \
  -F "images=@/path/to/image2.jpg"
```

**Response (201 Created):**
```json
{
  "id": 10,
  "name": "New Signature Dish",
  "price_formatted": "$18.99",
  ...
}
```

#### Update Dish (Chef/Manager Only)
```bash
curl -X PUT http://localhost:8000/dishes/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_CHEF_TOKEN" \
  -d '{
    "name": "Updated Dish Name",
    "price_cents": 1699,
    "is_available": false
  }'
```

#### Delete Dish (Chef/Manager Only)
```bash
curl -X DELETE http://localhost:8000/dishes/1 \
  -H "Authorization: Bearer YOUR_CHEF_TOKEN"
```

#### Rate a Dish (Must Have Ordered It)
```bash
curl -X POST http://localhost:8000/dishes/1/rate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "rating": 5,
    "order_id": 123,
    "review_text": "Absolutely delicious!"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Rating submitted successfully",
  "new_average_rating": 4.55,
  "review_count": 29
}
```

**Validation:**
- `rating`: Must be 1-5
- `order_id`: Must be a valid order belonging to the user
- The dish must have been part of the specified order
- Cannot rate the same dish twice for the same order

#### Add Images to Dish
```bash
curl -X POST http://localhost:8000/dishes/1/images \
  -H "Authorization: Bearer YOUR_CHEF_TOKEN" \
  -F "images=@/path/to/new_image.jpg"
```

### Home (Personalized Recommendations)

#### Get Personalized Home Content
```bash
# Unauthenticated: Returns global popular + top-rated dishes
curl http://localhost:8000/home

# Authenticated: Returns personalized recommendations
curl http://localhost:8000/home \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "most_ordered": [
    {"id": 1, "name": "Spaghetti Carbonara", "order_count": 156, ...},
    {"id": 3, "name": "Margherita Pizza", "order_count": 142, ...},
    {"id": 5, "name": "Tiramisu", "order_count": 98, ...}
  ],
  "top_rated": [
    {"id": 2, "name": "Truffle Risotto", "average_rating": 4.9, ...},
    {"id": 4, "name": "Seafood Linguine", "average_rating": 4.8, ...},
    {"id": 1, "name": "Spaghetti Carbonara", "average_rating": 4.5, ...}
  ],
  "is_personalized": true
}
```

**Personalization Logic:**
- **For customers with order history:**
  - `most_ordered`: Top 3 dishes this customer has ordered most frequently
  - `top_rated`: Top 3 dishes this customer has rated highest
- **For new users/visitors:**
  - `most_ordered`: Global most popular dishes by order count
  - `top_rated`: Global highest-rated dishes (minimum 1 review)

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
| `JWT_SECRET_KEY` | Secret key for JWT signing | dev-key (change in production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry in minutes | `60` |
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
