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

### Frontend Features (React + Vite + TypeScript + Tailwind CSS)
- ✅ **Authentication System**: Login/Register with JWT token management
- ✅ **Personalized Home Page**: Dish recommendations based on order history
- ✅ **Menu Browser**: Search, filter, sort, and paginated dish browsing
- ✅ **Dish Details**: Full dish information with image carousel and ratings
- ✅ **Shopping Cart**: Persistent cart with localStorage, quantity controls
- ✅ **Order Management**: Create orders with automatic balance deduction
- ✅ **AI Chat Support**: Knowledge base + LLM fallback with rating system
- ✅ **Role-Based Dashboards**: Manager (orders, bids), Chef (dishes), Delivery (assignments)
- ✅ **Warnings Banner**: Real-time account warnings display
- ✅ **Responsive Design**: Mobile-first approach with Tailwind CSS

### Backend Features (FastAPI + PostgreSQL)
- ✅ **RESTful API**: Complete CRUD operations for dishes, orders, users
- ✅ **JWT Authentication**: Role-based access control (Manager, Chef, Delivery, Customer, VIP)
- ✅ **Delivery Bidding System**: Competitive bidding with manager assignment
- ✅ **Chat System**: Full-text search knowledge base + LLM fallback
- ✅ **Reputation System**: Complaints, warnings, demotion, and firing logic
- ✅ **Voice Reporting**: Audio complaints with transcription and NLP analysis
- ✅ **VIP Benefits**: 5% discounts and free delivery credits
- ✅ **Transaction Audit**: Immutable financial transaction logging
- ✅ **Comprehensive Tests**: Unit and integration test coverage

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

### Test Accounts

| Email | Password | Role | Balance |
|-------|----------|------|---------|
| `manager@test.com` | `password123` | Manager | $5,000 |
| `chef@test.com` | `password123` | Chef | - |
| `delivery@test.com` | `password123` | Delivery | - |
| `customer@test.com` | `password123` | Customer | $100 |
| `vip@test.com` | `password123` | VIP | $1,000 |

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

### Orders API

#### List Orders
```bash
# List user's own orders (customers)
curl http://localhost:8000/orders \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by status
curl "http://localhost:8000/orders?status_filter=paid" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Pagination
curl "http://localhost:8000/orders?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "accountID": 5,
    "dateTime": "2025-12-01T10:30:00Z",
    "finalCost": 2500,
    "status": "paid",
    "bidID": null,
    "note": null,
    "delivery_address": "123 Main St",
    "delivery_fee": 500,
    "subtotal_cents": 2000,
    "discount_cents": 0,
    "free_delivery_used": 0,
    "ordered_dishes": [
      {"DishID": 1, "quantity": 2, "dish_name": "Spaghetti", "dish_cost": 1000}
    ]
  }
]
```

#### Create Order
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "items": [
      {"dish_id": 1, "qty": 2},
      {"dish_id": 3, "qty": 1}
    ],
    "delivery_address": "123 Main St, Apt 4B"
  }'
```

**Response (201 Created):**
```json
{
  "message": "Order created successfully",
  "order": {
    "id": 1,
    "accountID": 5,
    "dateTime": "2025-12-01T10:30:00Z",
    "finalCost": 4500,
    "status": "paid",
    "delivery_address": "123 Main St, Apt 4B",
    "delivery_fee": 500,
    "subtotal_cents": 4000,
    "discount_cents": 0,
    "free_delivery_used": 0,
    "ordered_dishes": [...]
  },
  "balance_deducted": 4500,
  "new_balance": 5500
}
```

**Business Logic:**
- **Subtotal**: Sum of (dish price × quantity) for all items
- **Delivery Fee**: $5.00 (500 cents) standard
- **VIP Discount**: 5% off subtotal for VIP customers
- **VIP Free Delivery**: Every 3 completed orders earns 1 free delivery credit
- **Deposit Check**: Order rejected if user balance < total cost

**Error Response (402 Payment Required):**
```json
{
  "detail": {
    "error": "insufficient_deposit",
    "warnings": 2,
    "required_amount": 4500,
    "current_balance": 1000,
    "shortfall": 3500
  }
}
```

> **Note**: Each insufficient deposit attempt increments the user's warning count.

#### Get Order Details
```bash
curl http://localhost:8000/orders/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Authorization**: Order owner, delivery personnel, or manager can view.

#### Submit Delivery Bid (Delivery Personnel Only)
```bash
curl -X POST http://localhost:8000/orders/1/bid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer DELIVERY_TOKEN" \
  -d '{"price_cents": 350, "estimated_minutes": 25}'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "deliveryPersonID": 4,
  "orderID": 1,
  "bidAmount": 350,
  "estimated_minutes": 25,
  "delivery_person_email": "delivery@example.com",
  "is_lowest": true
}
```

**Alternative: POST /bids (with order_id in body):**
```bash
curl -X POST http://localhost:8000/bids \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer DELIVERY_TOKEN" \
  -d '{"order_id": 1, "price_cents": 350, "estimated_minutes": 25}'
```

**Constraints:**
- Only delivery personnel can bid
- Order must be in "paid" status (open for bidding)
- One bid per delivery person per order

#### List Bids for Order (with Delivery Stats)
```bash
curl http://localhost:8000/orders/1/bids \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "order_id": 1,
  "lowest_bid_id": 1,
  "bids": [
    {
      "id": 1,
      "deliveryPersonID": 4,
      "bidAmount": 350,
      "estimated_minutes": 25,
      "is_lowest": true,
      "delivery_person": {
        "account_id": 4,
        "email": "fast@delivery.com",
        "average_rating": 4.8,
        "reviews": 50,
        "total_deliveries": 200,
        "on_time_deliveries": 185,
        "on_time_percentage": 92.5,
        "avg_delivery_minutes": 22,
        "warnings": 0
      }
    },
    {
      "id": 2,
      "deliveryPersonID": 5,
      "bidAmount": 400,
      "estimated_minutes": 30,
      "is_lowest": false,
      "delivery_person": {
        "account_id": 5,
        "email": "reliable@delivery.com",
        "average_rating": 4.5,
        "reviews": 30,
        "total_deliveries": 100,
        "on_time_deliveries": 88,
        "on_time_percentage": 88.0,
        "avg_delivery_minutes": 28,
        "warnings": 1
      }
    }
  ]
}
```

> Bids are sorted by bid amount (lowest first). Each bid includes full delivery person stats for manager decision-making.

#### Get Delivery Scoreboard (Manager Only)
```bash
curl "http://localhost:8000/bids/scoreboard?sort_by=rating" \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "account_id": 4,
    "email": "fast@delivery.com",
    "average_rating": 4.8,
    "reviews": 50,
    "total_deliveries": 200,
    "on_time_deliveries": 185,
    "on_time_percentage": 92.5,
    "avg_delivery_minutes": 22,
    "warnings": 0
  }
]
```

**Sort Options:** `rating`, `on_time`, `deliveries`

#### Assign Delivery (Manager Only)
```bash
curl -X POST http://localhost:8000/orders/1/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "delivery_id": 4
  }'
```

**Response (200 OK):**
```json
{
  "message": "Delivery assigned successfully",
  "order_id": 1,
  "assigned_delivery_id": 4,
  "bid_id": 1,
  "delivery_fee": 350,
  "order_status": "assigned",
  "is_lowest_bid": true,
  "memo_saved": false
}
```

**Assigning Non-Lowest Bid (Requires Justification Memo):**
```bash
curl -X POST http://localhost:8000/orders/1/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "delivery_id": 5,
    "memo": "Better on-time record and higher rating justifies the $0.50 premium"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Delivery assigned successfully",
  "order_id": 1,
  "assigned_delivery_id": 5,
  "bid_id": 2,
  "delivery_fee": 400,
  "order_status": "assigned",
  "is_lowest_bid": false,
  "memo_saved": true
}
```

**Business Rules:**
- Only managers can assign delivery
- Order must be in "paid" status
- Delivery person must have submitted a bid
- **If non-lowest bid is chosen, memo is required** (saved to database for audit)

### Manager UI

The frontend includes a manager dashboard at `/manager/orders`:
- View all orders awaiting assignment
- See bids with delivery person stats (rating, on-time %, warnings)
- Lowest bid highlighted in green
- Click "Assign" to select a delivery person
- Modal prompts for justification when assigning non-lowest bid

### Order Status Flow

```
[created] → insufficient deposit → rejected (warning++)
    ↓
  [paid] → deposit deducted, open for bidding
    ↓
[assigned] → manager assigned delivery person
    ↓
[delivered] → (future: delivery confirmed)
```

### Transaction Audit Log

All balance changes are recorded in the transactions table for audit purposes.

#### Get Transaction History
```bash
curl http://localhost:8000/account/transactions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by type
curl "http://localhost:8000/account/transactions?transaction_type=deposit" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "transactions": [
    {
      "id": 3,
      "accountID": 5,
      "amount_cents": -4500,
      "balance_before": 10000,
      "balance_after": 5500,
      "transaction_type": "order_payment",
      "reference_type": "order",
      "reference_id": 1,
      "description": "Payment for order #1",
      "created_at": "2025-12-01T10:30:00Z"
    },
    {
      "id": 2,
      "accountID": 5,
      "amount_cents": 5000,
      "balance_before": 5000,
      "balance_after": 10000,
      "transaction_type": "deposit",
      "reference_type": "deposit",
      "reference_id": null,
      "description": "Deposit of $50.00",
      "created_at": "2025-12-01T09:00:00Z"
    }
  ],
  "total": 2
}
```

**Transaction Types:**
- `deposit`: User deposited funds
- `withdrawal`: User withdrew funds
- `order_payment`: Payment for an order

### Reputation & HR API

The reputation system handles complaints, compliments, warnings, and employee management.

#### File a Complaint or Compliment
```bash
curl -X POST http://localhost:8000/complaints \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "about_user_id": 5,
    "order_id": 123,
    "type": "complaint",
    "text": "Food was cold when delivered"
  }'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "accountID": 5,
  "type": "complaint",
  "description": "Food was cold when delivered",
  "filer": 3,
  "filer_email": "customer@example.com",
  "about_email": "delivery@example.com",
  "order_id": 123,
  "status": "pending",
  "resolution": null,
  "created_at": "2025-12-01T15:30:00Z"
}
```

**Parameters:**
- `about_user_id`: User being complained about (null for general complaints)
- `order_id`: Related order (optional)
- `type`: "complaint" or "compliment"
- `text`: Description (1-2000 characters)

#### List Complaints (Manager Only)
```bash
curl "http://localhost:8000/complaints?status_filter=pending" \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "complaints": [...],
  "total": 15,
  "unresolved_count": 8
}
```

#### Resolve a Complaint (Manager Only)
```bash
curl -X PATCH http://localhost:8000/complaints/1/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "resolution": "warning_issued",
    "notes": "Verified late delivery, warning issued to delivery person"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Complaint resolved as warning_issued",
  "complaint_id": 1,
  "resolution": "warning_issued",
  "warning_applied_to": 5,
  "warning_count": 2,
  "account_status_changed": null,
  "audit_log_id": 42
}
```

**Resolution Types:**
- `warning_issued`: Valid complaint → target user receives warning
- `dismissed`: Complaint without merit → **complainant** receives warning

#### Business Rules

| User Type | Warning Threshold | Consequence |
|-----------|-------------------|-------------|
| Customer | 3 warnings | Deregistered and blacklisted |
| VIP | 2 warnings | Demoted to regular customer, warnings cleared |
| Chef | 3 complaints OR rating <2.0 | Demoted (10% wage reduction) |
| Chef | Demoted twice | Fired |

**Compliment Cancellation:**
- Compliments can cancel pending complaints one-for-one
- Both are marked as resolved when canceled

#### Login Warning Display

When logging in, users with warnings see a message:
```json
{
  "access_token": "...",
  "warning_info": {
    "warnings_count": 2,
    "warning_message": "You have 2 warning(s). Reaching 3 warnings will result in account suspension.",
    "is_near_threshold": true
  }
}
```

**Blocked Logins:**
- Blacklisted users: "This account has been permanently suspended"
- Fired employees: "This employee account has been terminated"

#### View Audit Logs (Manager Only)
```bash
curl "http://localhost:8000/complaints/audit/logs?limit=20" \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "entries": [
    {
      "id": 42,
      "action_type": "complaint_resolved",
      "actor_id": 1,
      "target_id": 5,
      "complaint_id": 1,
      "details": {
        "resolution": "warning_issued",
        "warning_count": 2
      },
      "created_at": "2025-12-01T15:45:00Z"
    }
  ],
  "total": 42
}
```

**Action Types:**
- `complaint_filed`, `compliment_filed`
- `complaint_resolved`
- `warning_issued`, `customer_blacklisted`
- `vip_demoted`, `chef_demoted`, `chef_fired`
- `complaint_canceled_by_compliment`

#### Manager Notifications
```bash
# List notifications
curl "http://localhost:8000/complaints/notifications?unread_only=true" \
  -H "Authorization: Bearer MANAGER_TOKEN"

# Mark as read
curl -X PATCH http://localhost:8000/complaints/notifications/1/read \
  -H "Authorization: Bearer MANAGER_TOKEN"

# Mark all as read
curl -X POST http://localhost:8000/complaints/notifications/read-all \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

#### Trigger Chef/Delivery Evaluation (Manager Only)
```bash
curl -X POST http://localhost:8000/admin/evaluate-performance \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "message": "Performance evaluation completed",
  "results": {
    "chef_evaluations": [
      {
        "chef_id": 2,
        "email": "chef1@example.com",
        "complaint_count": 1,
        "avg_rating": 4.2,
        "times_demoted": 0,
        "status": "ok"
      }
    ],
    "delivery_evaluations": [...],
    "timestamp": "2025-12-01T16:00:00Z"
  }
}
```

**Automatic Evaluation:**
- Background task runs every hour
- Creates notifications for employees nearing thresholds
- Status levels: `ok`, `warning` (near threshold), `critical` (at threshold)

#### Manager Complaints UI

Access at `/manager/complaints`:
- View all pending complaints
- Filter by status and type
- Click to see full details
- Resolve with dismiss (warn complainant) or issue warning (warn target)
- See real-time status changes and audit references

### AI Features (Coming Soon)
- `POST /api/ai/recommend` - Get menu recommendations
- `POST /api/ai/chat` - Natural language interaction

### Image Search API

The image search system allows users to upload photos of food and find similar dishes in the database.

#### Search for Dishes by Image
```bash
curl -X POST http://localhost:8000/image-search \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/food_photo.jpg" \
  -F "top_k=5"
```

**Response (200 OK):**
```json
[
  {
    "id": 3,
    "name": "Margherita Pizza",
    "description": "Classic pizza with tomato, mozzarella, and basil",
    "cost": 1299,
    "cost_formatted": "$12.99",
    "picture": "/static/images/pizza.jpg",
    "average_rating": 4.7,
    "reviews": 89,
    "chefID": 2,
    "restaurantID": 1,
    "similarity_score": 0.8542
  },
  {
    "id": 7,
    "name": "Pepperoni Pizza",
    "description": "Traditional pepperoni pizza",
    "cost": 1399,
    "cost_formatted": "$13.99",
    "picture": "/static/images/pepperoni.jpg",
    "average_rating": 4.5,
    "reviews": 67,
    "chefID": 2,
    "restaurantID": 1,
    "similarity_score": 0.7821
  }
]
```

**Implementation Details:**
- **Default Method**: Color histogram matching (works out-of-the-box)
  - Extracts RGB color distributions
  - Compares using chi-squared distance
  - Fast and requires no external models

- **Hugging Face Vision Model** (nateraw/food)
  - Specialized food classification model
  - Better accuracy for food items
  - Requires `transformers` library
  - Set `USE_HUGGINGFACE=True` in `app/image_utils.py`

- **CLIP Embeddings** (Best Accuracy)
  - Semantic similarity matching
  - Understands visual concepts beyond just colors
  - Can run locally or as a microservice
  - Set `USE_CLIP=True` in `app/image_utils.py`

**File Requirements:**
- Supported formats: JPG, JPEG, PNG, WebP, GIF
- Maximum size: 10MB
- Must be authenticated

#### Get Image Search Status
```bash
curl http://localhost:8000/image-search/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (200 OK):**
```json
{
  "method": "color histograms",
  "total_dishes": 25,
  "dishes_with_images": 20,
  "cached_features": 20,
  "ready": true,
  "max_file_size_mb": 10,
  "supported_formats": ["jpg", "jpeg", "png", "webp", "gif"]
}
```

#### Precompute Dish Features (Manager Only)
```bash
curl -X POST http://localhost:8000/image-search/precompute \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "message": "Successfully precomputed features for 20 dishes",
  "method": "color histograms",
  "dish_count": 20
}
```

**When to use:**
- After adding new dishes with images
- When switching between histogram and CLIP mode
- To rebuild the feature cache

#### Upgrading to CLIP

**Option 1: Local CLIP (Easiest)**

1. Install dependencies:
```bash
docker-compose exec backend pip install torch torchvision transformers
```

2. Enable CLIP in the code:
```python
# In backend/app/image_utils.py, line 27
USE_CLIP = True  # Change from False to True
```

3. Restart backend:
```bash
docker-compose restart backend
```

4. Precompute features with CLIP:
```bash
curl -X POST http://localhost:8000/image-search/precompute \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Option 2: CLIP Service (Production)**

For better isolation and scalability, run CLIP as a separate service:

1. Add to `docker-compose.yml`:
```yaml
  clip-service:
    build: ./clip-service
    ports:
      - "8002:8002"
    environment:
      - MODEL_NAME=openai/clip-vit-base-patch32
    volumes:
      - ./clip-service/cache:/root/.cache
```

2. Create the service files:
```bash
docker-compose exec backend python -c "
from app.clip_adapter import save_clip_service_code
save_clip_service_code('./clip-service')
"
```

3. Update environment:
```bash
# Add to .env
CLIP_SERVICE_URL=http://clip-service:8002
USE_CLIP=true
```

4. Start the service:
```bash
docker-compose up --build clip-service
```

**Performance Comparison:**

| Method | Accuracy | Speed | Dependencies |
|--------|----------|-------|--------------|
| Color Histograms | Basic | Fast (~10ms) | None (Pillow only) |
| HF Vision Model | Good | Moderate (~80ms CPU) | torch, transformers (~500MB) |
| CLIP Embeddings | Excellent | Moderate (~100ms CPU) | torch, transformers (~1GB) |

**Example Results:**

*Query: Photo of red curry*
- **Histogram**: Matches red-colored dishes (tomato soup, red curry, strawberry dessert)
- **HF Vision**: Matches food types (curry, soup, stew)
- **CLIP**: Matches semantically similar dishes (red curry, yellow curry, pad thai)

#### Frontend Integration

The image search page is accessible at `/image-search` and includes:
- Drag-and-drop or click to upload
- Image preview before search
- Loading states with skeleton UI
- Results displayed as cards with similarity scores
- Direct links to dish detail pages

**Example Usage:**
1. Navigate to http://localhost:3000/image-search
2. Upload a food photo (or drag & drop)
3. Click "Search for Similar Dishes"
4. Browse top 5 matching dishes
5. Click any result to view full details and add to cart

### Voice Reporting API

The voice reporting system allows users to submit audio complaints or compliments, which are automatically transcribed and analyzed using NLP.

#### Submit Voice Report
```bash
curl -X POST http://localhost:8000/voice-reports/submit \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "audio_file=@/path/to/recording.mp3" \
  -F "related_order_id=123"
```

**Response (200 OK):**
```json
{
  "message": "Voice report submitted successfully. Processing will begin shortly.",
  "report_id": 42,
  "status": "pending"
}
```

**Features:**
- **Automatic Transcription**: Converts speech to text
- **NLP Analysis**: Detects sentiment (complaint/compliment) and extracts subjects (e.g., "delivery", "food quality")
- **Auto-Labeling**: Tags reports for easier filtering

#### Manager Dashboard (Voice)
```bash
curl "http://localhost:8000/voice-reports/manager/dashboard?sentiment=complaint" \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "reports": [
    {
      "id": 42,
      "transcription": "The delivery was very fast and the driver was polite.",
      "sentiment": "compliment",
      "subjects": ["delivery", "driver"],
      "audio_url": "/voice-reports/audio/42",
      "status": "analyzed"
    }
  ]
}
```

#### Resolve Voice Report (Manager Only)
```bash
curl -X POST http://localhost:8000/voice-reports/42/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "action": "warning",
    "related_account_id": 5,
    "notes": "Driver was rude based on audio evidence"
  }'
```

**Actions:** `dismiss`, `warning`, `refer_to_complaint`

### Chat & Knowledge Base API

The chat system provides AI-powered Q&A with knowledge base search and LLM fallback.

#### Query the Chat System
```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "question": "What are your hours of operation?"
  }'
```

**Response (200 OK) - KB Match:**
```json
{
  "chat_id": 1,
  "question": "What are your hours of operation?",
  "answer": "We are open Monday through Sunday from 11:00 AM to 10:00 PM. Last orders are taken at 9:30 PM.",
  "source": "kb",
  "confidence": 0.85,
  "kb_entry_id": 1
}
```

**Response (200 OK) - LLM Fallback:**
```json
{
  "chat_id": 2,
  "question": "What's your most exotic dish?",
  "answer": "I'd be happy to help you with that! Based on our restaurant's offerings, I recommend checking out our daily specials.",
  "source": "llm",
  "confidence": 0.5,
  "kb_entry_id": null
}
```

**Flow:**
1. Search knowledge base using PostgreSQL full-text search
2. If high-confidence match found (≥0.6), return KB answer
3. If no match, call configured LLM adapter (stub/Ollama/HuggingFace)
4. Store chat log and return `chat_id` for rating

#### Rate a Chat Response
```bash
curl -X POST http://localhost:8000/chat/1/rate \
  -H "Content-Type: application/json" \
  -d '{"rating": 5}'
```

**Response (200 OK):**
```json
{
  "message": "Rating recorded",
  "chat_id": 1,
  "rating": 5,
  "flagged": false
}
```

**Rating = 0 Flags for Review:**
```bash
curl -X POST http://localhost:8000/chat/1/rate \
  -H "Content-Type: application/json" \
  -d '{"rating": 0}'
```

**Response:**
```json
{
  "message": "Flagged for manager review",
  "chat_id": 1,
  "rating": 0,
  "flagged": true
}
```

#### View Flagged Chats (Manager Only)
```bash
curl http://localhost:8000/chat/flagged \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (200 OK):**
```json
{
  "flagged_chats": [
    {
      "id": 1,
      "user_id": 5,
      "user_email": "customer@example.com",
      "question": "What are your hours?",
      "answer": "We are open 24/7",
      "source": "kb",
      "confidence": 0.75,
      "rating": 0,
      "kb_entry_id": 3,
      "created_at": "2025-12-01T10:30:00Z",
      "reviewed": false
    }
  ],
  "total": 1
}
```

#### Review Flagged Chat (Manager Only)
```bash
# Dismiss - just mark as reviewed
curl -X POST http://localhost:8000/chat/1/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{"action": "dismiss"}'

# Remove KB entry - deactivate the problematic answer
curl -X POST http://localhost:8000/chat/1/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{"action": "remove_kb"}'

# Disable author - deactivate ALL KB entries by this author
curl -X POST http://localhost:8000/chat/1/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{"action": "disable_author"}'
```

**Response (200 OK):**
```json
{
  "message": "Chat 1 reviewed",
  "chat_id": 1,
  "action_taken": "remove_kb",
  "kb_entries_affected": 1
}
```

#### Knowledge Base CRUD (Manager Only)

**List KB Entries:**
```bash
curl "http://localhost:8000/chat/kb?active_only=true" \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Create KB Entry:**
```bash
curl -X POST http://localhost:8000/chat/kb \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "question": "Do you have parking?",
    "answer": "Yes, free parking is available behind the building.",
    "keywords": "parking,park,car,lot",
    "confidence": 0.9
  }'
```

**Update KB Entry:**
```bash
curl -X PUT http://localhost:8000/chat/kb/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "answer": "Updated answer text",
    "confidence": 0.95
  }'
```

**Delete KB Entry (Soft Delete):**
```bash
curl -X DELETE http://localhost:8000/chat/kb/1 \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

#### LLM Adapter Health & Cache (Manager Only)
```bash
# Check adapter status
curl http://localhost:8000/chat/adapter/health \
  -H "Authorization: Bearer MANAGER_TOKEN"

# Clear LLM response cache
curl -X POST http://localhost:8000/chat/adapter/cache/clear \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

**Response (Adapter Health):**
```json
{
  "adapter": {
    "status": "ok",
    "adapter": "stub",
    "service": "connected"
  },
  "cache": {
    "entries": 15,
    "max_entries": 1000,
    "total_hits": 42,
    "ttl_seconds": 3600
  }
}
```

### LLM Adapter Configuration

The chat system uses a pluggable LLM adapter. Configure via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_ADAPTER` | Adapter type: `stub`, `ollama`, `huggingface` | `stub` |
| `LLM_STUB_URL` | URL for stub service | `http://llm-stub:8001` |
| `OLLAMA_URL` | URL for Ollama API | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama2` |
| `HF_MODEL` | HuggingFace model name | `gpt2` |
| `LLM_CACHE_TTL` | Cache TTL in seconds | `3600` |
| `KB_CONFIDENCE_THRESHOLD` | Min confidence for KB match | `0.6` |

#### Using Ollama

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama2`
3. Start Ollama: `ollama serve`
4. Set environment:
   ```bash
   export LLM_ADAPTER=ollama
   export OLLAMA_URL=http://localhost:11434
   export OLLAMA_MODEL=llama2
   ```

#### Using HuggingFace (Local)

1. Install transformers: `pip install transformers torch`
2. Set environment:
   ```bash
   export LLM_ADAPTER=huggingface
   export HF_MODEL=gpt2  # or any text-generation model
   ```

> **Note:** HuggingFace runs models locally and requires sufficient RAM/GPU.

### Seeding Knowledge Base

Load initial FAQ data:
```bash
docker-compose exec postgres psql -U restaurant_user -d restaurant_db \
  -f /app/sql/seed_knowledge_base.sql
```

This adds ~15 common Q&A entries covering hours, ordering, delivery, payment, and more.

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
- [x] Authentication (JWT)
- [x] Dishes API with images
- [x] Order management API
- [x] Delivery bidding system
- [x] VIP discounts & free delivery
- [x] Transaction audit logging
- [x] Reputation & HR system
  - [x] Complaint/compliment filing
  - [x] Manager resolution UI
  - [x] Warning thresholds (customer blacklist, VIP demotion)
  - [x] Chef performance tracking (demotion/firing)
  - [x] Compliment cancellation
  - [x] Immutable audit log
  - [x] Login warning display
  - [x] Background performance evaluation
- [x] Chat & Knowledge Base System
  - [x] Knowledge base with full-text search
  - [x] Chat query endpoint with KB search + LLM fallback
  - [x] Rating system (0 = flag for review)
  - [x] Manager flagged answer review
  - [x] Pluggable LLM adapters (Stub, Ollama, HuggingFace)
  - [x] LLM response caching
  - [x] KB CRUD endpoints
- [x] Image-Based Food Search
  - [x] Color histogram baseline (no dependencies)
  - [x] Image upload & validation
  - [x] Similarity matching & ranking
  - [x] Frontend image search page
  - [x] CLIP integration option (local + service)
  - [x] Feature caching & precomputation
- [x] Voice Reporting System
  - [x] Audio file upload & validation
  - [x] Automatic transcription (Stub/Whisper)
  - [x] NLP analysis (Sentiment & Subjects)
  - [x] Manager dashboard for voice reports
  - [x] Resolution workflow (Warning/Complaint)
- [ ] Menu management API
- [ ] AI recommendation integration
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
