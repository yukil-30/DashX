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
│   ├── tests/
│   │   └── test_health.py
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

## 🔄 Roadmap

- [x] Project skeleton with Docker Compose
- [x] Backend FastAPI with health check
- [x] Frontend React + TypeScript
- [x] LLM Stub service
- [ ] Database models and migrations
- [ ] Menu management API
- [ ] Order management API
- [ ] AI recommendation integration
- [ ] Replace LLM stub with Ollama
- [ ] Kitchen dashboard UI
- [ ] Real-time order updates (WebSocket)

## 📄 License

This project is for educational purposes as part of a Software Engineering course.
