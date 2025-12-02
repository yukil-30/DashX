# DashX Database Schema Documentation

## Overview

This document describes the PostgreSQL database schema for the DashX restaurant management system. The schema supports:
- Multi-role user management (visitors, customers, VIP, chefs, delivery, managers)
- Menu and dish management with reviews and ratings
- Order processing with delivery bidding system
- Financial transactions and audit trail
- Complaint/compliment system
- Discussion forums
- AI query/answer system

---

## Entity-Relationship Summary

### Tables and Relationships

```
┌─────────────────┐
│   restaurant    │
│─────────────────│
│ PK: id          │
│ name            │
│ address         │
│ phone           │
│ email           │
│ opening_hours   │
└────────┬────────┘
         │
    ┌────┴─────────────────────────────────────────────┐
    │                                                  │
    ▼                                                  ▼
┌─────────────────┐                          ┌─────────────────┐
│    accounts     │                          │     dishes      │
│─────────────────│                          │─────────────────│
│ PK: id          │◄─────────────────────────│ FK: chef_id     │
│ FK: restaurant_id                          │ FK: restaurant_id
│ email (UNIQUE)  │                          │ PK: id          │
│ account_type    │                          │ name            │
│ balance         │                          │ price           │
│ warnings        │                          │ average_rating  │
│ is_blacklisted  │                          └────────┬────────┘
└────────┬────────┘                                   │
         │                                            │
    ┌────┴────┐                              ┌────────┴────────┐
    │         │                              │                 │
    ▼         ▼                              ▼                 ▼
┌─────────┐ ┌─────────┐             ┌─────────────┐    ┌─────────────┐
│ orders  │ │  bids   │             │dish_reviews │    │ordered_dishes
│─────────│ │─────────│             │─────────────│    │─────────────│
│ PK: id  │◄│FK:order │             │FK: dish_id  │    │FK: order_id │
│FK:acct  │ │FK:deliv │             │FK: account  │    │FK: dish_id  │
│FK:bid   │ │ amount  │             │ rating      │    │ quantity    │
│ status  │ │ status  │             │ review_text │    │ unit_price  │
└────┬────┘ └─────────┘             └─────────────┘    └─────────────┘
     │
     ├──────────────────────┐
     │                      │
     ▼                      ▼
┌──────────────┐    ┌────────────────┐
│ transactions │    │delivery_ratings│
│──────────────│    │────────────────│
│FK: account_id│    │FK: delivery_id │
│FK: order_id  │    │FK: order_id    │
│ type, amount │    │FK: rater_id    │
│ balance_*    │    │ rating         │
└──────────────┘    └────────────────┘

┌─────────────────┐     ┌─────────────────┐
│   complaints    │     │     threads     │
│─────────────────│     │─────────────────│
│FK: about_acct   │     │ PK: id          │
│FK: reporter_acct│     │FK: restaurant_id│
│FK: order_id     │     │FK: created_by   │
│ type (enum)     │     │ topic           │
│ is_resolved     │     └────────┬────────┘
└─────────────────┘              │
                                 ▼
                        ┌─────────────────┐
                        │     posts       │
                        │─────────────────│
                        │FK: thread_id    │
                        │FK: poster_id    │
                        │FK: parent_post  │
                        │ title, body     │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  agent_queries  │     │  agent_answers  │
│─────────────────│     │─────────────────│
│ PK: id          │◄────│FK: query_id     │
│FK: account_id   │     │FK: author_id    │
│FK: restaurant_id│     │ answer          │
│ question        │     │ average_rating  │
└─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  open_requests  │     │closure_requests │
│─────────────────│     │─────────────────│
│FK: restaurant_id│     │FK: account_id   │
│ email           │     │ reason          │
│ requested_role  │     │ status          │
│ status          │     └─────────────────┘
└─────────────────┘

┌─────────────────┐
│   vip_history   │
│─────────────────│
│FK: account_id   │
│FK: changed_by   │
│ previous_type   │
│ new_type        │
└─────────────────┘
```

---

## Table Definitions

### 1. restaurant
Central entity for restaurant information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Restaurant name |
| address | TEXT | NOT NULL | Physical address |
| phone | VARCHAR(20) | | Contact phone |
| email | VARCHAR(255) | | Contact email |
| description | TEXT | | About the restaurant |
| opening_hours | JSONB | | Flexible hours storage |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | Active status |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Last update timestamp |

### 2. accounts
All system users: visitors, customers, VIPs, and employees.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| restaurant_id | INTEGER | FK -> restaurant(id) | For employees only |
| email | VARCHAR(255) | NOT NULL, UNIQUE | Login email |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt/Argon2 hash |
| first_name | VARCHAR(100) | | User's first name |
| last_name | VARCHAR(100) | | User's last name |
| phone | VARCHAR(20) | | Contact phone |
| address | TEXT | | Delivery address |
| account_type | account_type | NOT NULL DEFAULT 'visitor' | User role |
| balance | INTEGER | NOT NULL DEFAULT 0 | Balance in cents |
| wage | INTEGER | | Hourly wage in cents |
| warnings | INTEGER | NOT NULL DEFAULT 0 | Warning count |
| is_blacklisted | BOOLEAN | NOT NULL DEFAULT FALSE | Blacklist status |
| free_delivery_credits | INTEGER | NOT NULL DEFAULT 0 | Promo credits |
| last_login_at | TIMESTAMPTZ | | Last login time |
| created_at | TIMESTAMPTZ | NOT NULL | Account creation |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

**ENUM: account_type**
- `visitor` - Browsing only
- `customer` - Can place orders
- `vip` - Premium customer with perks
- `chef` - Kitchen staff
- `delivery` - Delivery personnel
- `manager` - Restaurant management

### 3. dishes
Menu items available for ordering.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| restaurant_id | INTEGER | NOT NULL, FK -> restaurant(id) | Owner restaurant |
| chef_id | INTEGER | FK -> accounts(id) | Creating chef |
| name | VARCHAR(255) | NOT NULL | Dish name |
| description | TEXT | | Dish description |
| price | INTEGER | NOT NULL CHECK >= 0 | Price in cents |
| picture | TEXT | | Image URL/path |
| category | VARCHAR(100) | | appetizer/main/etc |
| is_available | BOOLEAN | NOT NULL DEFAULT TRUE | Availability |
| is_special | BOOLEAN | NOT NULL DEFAULT FALSE | Featured dish |
| average_rating | NUMERIC(3,2) | CHECK 0-5 | Avg user rating |
| review_count | INTEGER | NOT NULL DEFAULT 0 | Number of reviews |
| created_at | TIMESTAMPTZ | NOT NULL | Creation time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

### 4. orders
Customer orders.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| account_id | INTEGER | NOT NULL, FK -> accounts(id) | Customer placing order |
| restaurant_id | INTEGER | NOT NULL, FK -> restaurant(id) | Restaurant |
| order_datetime | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Order time |
| final_cost | INTEGER | NOT NULL CHECK >= 0 | Total in cents |
| subtotal | INTEGER | NOT NULL CHECK >= 0 | Before fees |
| delivery_fee | INTEGER | NOT NULL DEFAULT 0 | Delivery fee |
| tip | INTEGER | NOT NULL DEFAULT 0 | Tip amount |
| discount | INTEGER | NOT NULL DEFAULT 0 | Discount applied |
| status | order_status | NOT NULL DEFAULT 'pending' | Order state |
| accepted_bid_id | INTEGER | FK -> bids(id) | Accepted delivery bid |
| delivery_address | TEXT | | Delivery location |
| note | TEXT | | Special instructions |
| is_delivery | BOOLEAN | NOT NULL DEFAULT TRUE | Delivery vs pickup |
| estimated_ready_time | TIMESTAMPTZ | | ETA |
| actual_ready_time | TIMESTAMPTZ | | Actual completion |
| delivered_at | TIMESTAMPTZ | | Delivery timestamp |
| created_at | TIMESTAMPTZ | NOT NULL | Creation |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

**ENUM: order_status**
- `pending`, `confirmed`, `preparing`, `ready`, `out_for_delivery`, `delivered`, `cancelled`, `refunded`

### 5. ordered_dishes
Junction table linking orders to dishes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| order_id | INTEGER | NOT NULL, FK -> orders(id) CASCADE | Parent order |
| dish_id | INTEGER | NOT NULL, FK -> dishes(id) RESTRICT | Ordered dish |
| quantity | INTEGER | NOT NULL CHECK > 0 | Quantity ordered |
| unit_price | INTEGER | NOT NULL | Price at order time |
| special_instructions | TEXT | | Item-specific notes |
| created_at | TIMESTAMPTZ | NOT NULL | Creation |

### 6. bids
Delivery person bids on orders.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| order_id | INTEGER | NOT NULL, FK -> orders(id) CASCADE | Target order |
| delivery_person_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Bidding driver |
| bid_amount | INTEGER | NOT NULL CHECK >= 0 | Bid amount in cents |
| status | bid_status | NOT NULL DEFAULT 'pending' | Bid state |
| notes | TEXT | | Bid notes |
| created_at | TIMESTAMPTZ | NOT NULL | Bid time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

**Unique constraint:** (order_id, delivery_person_id) - One bid per driver per order

**ENUM: bid_status**
- `pending`, `accepted`, `rejected`, `expired`

### 7. complaints
Unified complaints and compliments table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| about_account_id | INTEGER | NOT NULL, FK -> accounts(id) | Subject of feedback |
| reporter_account_id | INTEGER | NOT NULL, FK -> accounts(id) | Person filing |
| order_id | INTEGER | FK -> orders(id) | Related order (optional) |
| feedback_type | feedback_type | NOT NULL | complaint/compliment |
| description | TEXT | NOT NULL | Details |
| is_resolved | BOOLEAN | NOT NULL DEFAULT FALSE | Resolution status |
| manager_decision | TEXT | | Manager's action |
| resolved_by_id | INTEGER | FK -> accounts(id) | Resolving manager |
| resolved_at | TIMESTAMPTZ | | Resolution time |
| created_at | TIMESTAMPTZ | NOT NULL | Filing time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

**Check constraint:** about_account_id != reporter_account_id

**ENUM: feedback_type**
- `complaint`, `compliment`

### 8. threads
Forum discussion threads.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| restaurant_id | INTEGER | NOT NULL, FK -> restaurant(id) CASCADE | Restaurant forum |
| topic | VARCHAR(255) | NOT NULL | Thread topic |
| created_by_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Thread creator |
| is_pinned | BOOLEAN | NOT NULL DEFAULT FALSE | Pinned status |
| is_locked | BOOLEAN | NOT NULL DEFAULT FALSE | Comments locked |
| view_count | INTEGER | NOT NULL DEFAULT 0 | View counter |
| created_at | TIMESTAMPTZ | NOT NULL | Creation |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

### 9. posts
Forum posts within threads.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| thread_id | INTEGER | NOT NULL, FK -> threads(id) CASCADE | Parent thread |
| poster_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Post author |
| parent_post_id | INTEGER | FK -> posts(id) CASCADE | For nested replies |
| title | VARCHAR(255) | | Post title (optional) |
| body | TEXT | NOT NULL | Post content |
| is_edited | BOOLEAN | NOT NULL DEFAULT FALSE | Edit indicator |
| created_at | TIMESTAMPTZ | NOT NULL | Post time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

### 10. agent_queries
AI/LLM queries from users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| account_id | INTEGER | FK -> accounts(id) | Querying user |
| restaurant_id | INTEGER | FK -> restaurant(id) CASCADE | Context restaurant |
| question | TEXT | NOT NULL | User's question |
| context | JSONB | | Additional context |
| created_at | TIMESTAMPTZ | NOT NULL | Query time |

### 11. agent_answers
AI/LLM responses to queries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| query_id | INTEGER | NOT NULL, FK -> agent_queries(id) CASCADE | Parent query |
| author_id | INTEGER | FK -> accounts(id) | NULL for AI answers |
| answer | TEXT | NOT NULL | Answer content |
| is_ai_generated | BOOLEAN | NOT NULL DEFAULT TRUE | AI vs human |
| average_rating | NUMERIC(3,2) | CHECK 0-5 | User rating |
| review_count | INTEGER | NOT NULL DEFAULT 0 | Rating count |
| created_at | TIMESTAMPTZ | NOT NULL | Answer time |

### 12. delivery_ratings
Ratings for delivery personnel.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| delivery_person_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Rated driver |
| order_id | INTEGER | NOT NULL, FK -> orders(id) CASCADE | Related order |
| rater_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Rating customer |
| rating | INTEGER | NOT NULL CHECK 1-5 | Star rating |
| comment | TEXT | | Review text |
| created_at | TIMESTAMPTZ | NOT NULL | Rating time |

**Unique constraint:** (order_id, rater_id)

### 13. dish_reviews
Customer reviews for dishes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| dish_id | INTEGER | NOT NULL, FK -> dishes(id) CASCADE | Reviewed dish |
| account_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Reviewer |
| order_id | INTEGER | FK -> orders(id) | Related order |
| rating | INTEGER | NOT NULL CHECK 1-5 | Star rating |
| review_text | TEXT | | Review content |
| created_at | TIMESTAMPTZ | NOT NULL | Review time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

**Unique constraint:** (dish_id, account_id, order_id)

### 14. open_requests
Employee job applications.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| restaurant_id | INTEGER | NOT NULL, FK -> restaurant(id) CASCADE | Target restaurant |
| email | VARCHAR(255) | NOT NULL | Applicant email |
| password_hash | VARCHAR(255) | NOT NULL | Temp password hash |
| first_name | VARCHAR(100) | NOT NULL | First name |
| last_name | VARCHAR(100) | NOT NULL | Last name |
| phone | VARCHAR(20) | | Contact phone |
| requested_role | account_type | NOT NULL | Desired position |
| resume_url | TEXT | | Resume link |
| cover_letter | TEXT | | Application letter |
| status | VARCHAR(20) | CHECK IN ('pending','approved','rejected') | Application status |
| reviewed_by_id | INTEGER | FK -> accounts(id) | Reviewing manager |
| reviewed_at | TIMESTAMPTZ | | Review time |
| rejection_reason | TEXT | | If rejected |
| created_at | TIMESTAMPTZ | NOT NULL | Submission time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

### 15. closure_requests
Account deletion requests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| account_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | Requesting user |
| reason | TEXT | | Closure reason |
| status | VARCHAR(20) | CHECK IN ('pending','approved','rejected') | Request status |
| reviewed_by_id | INTEGER | FK -> accounts(id) | Reviewing manager |
| reviewed_at | TIMESTAMPTZ | | Review time |
| rejection_reason | TEXT | | If rejected |
| created_at | TIMESTAMPTZ | NOT NULL | Request time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update |

### 16. transactions
Financial audit trail (recommended for any financial system).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| account_id | INTEGER | NOT NULL, FK -> accounts(id) RESTRICT | Account affected |
| order_id | INTEGER | FK -> orders(id) | Related order |
| transaction_type | transaction_type | NOT NULL | Type of transaction |
| amount | INTEGER | NOT NULL | Amount in cents (+/-) |
| balance_before | INTEGER | NOT NULL | Previous balance |
| balance_after | INTEGER | NOT NULL | New balance |
| description | TEXT | | Transaction notes |
| reference_id | VARCHAR(100) | | External reference |
| created_at | TIMESTAMPTZ | NOT NULL | Transaction time |

**ENUM: transaction_type**
- `deposit`, `withdrawal`, `order_payment`, `order_refund`, `wage_payment`, `tip`, `delivery_fee`

### 17. vip_history
Track VIP status changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| account_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | User |
| previous_type | account_type | NOT NULL | Old account type |
| new_type | account_type | NOT NULL | New account type |
| reason | TEXT | | Reason for change |
| changed_by_id | INTEGER | FK -> accounts(id) | Manager who changed |
| created_at | TIMESTAMPTZ | NOT NULL | Change time |

### 18. voice_reports
Voice-based complaint/compliment system with automatic transcription and NLP analysis.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| submitter_id | INTEGER | NOT NULL, FK -> accounts(id) CASCADE | User who submitted |
| audio_file_path | TEXT | NOT NULL | Path to stored audio file |
| file_size_bytes | INTEGER | NOT NULL | File size in bytes |
| duration_seconds | INTEGER | | Audio duration |
| mime_type | VARCHAR(100) | NOT NULL DEFAULT 'audio/mpeg' | Audio MIME type |
| transcription | TEXT | | Transcribed text |
| sentiment | VARCHAR(50) | | complaint, compliment, neutral |
| subjects | JSONB | | Extracted subjects array |
| auto_labels | JSONB | | Auto-generated label array |
| confidence_score | NUMERIC(3,2) | CHECK 0-1 | NLP confidence |
| status | VARCHAR(50) | NOT NULL DEFAULT 'pending' | Processing status |
| is_processed | BOOLEAN | NOT NULL DEFAULT FALSE | Processing complete |
| related_order_id | INTEGER | FK -> orders(id) SET NULL | Related order |
| related_account_id | INTEGER | FK -> accounts(id) SET NULL | Person being reported |
| processing_error | TEXT | | Error message if failed |
| manager_notes | TEXT | | Manager resolution notes |
| resolved_by | INTEGER | FK -> accounts(id) SET NULL | Resolving manager |
| resolved_at | TEXT | | ISO timestamp |
| created_at | TEXT | NOT NULL | ISO timestamp |
| updated_at | TEXT | NOT NULL | ISO timestamp |

**Status values:** `pending`, `transcribed`, `analyzed`, `resolved`, `error`

**Sentiment values:** `complaint`, `compliment`, `neutral`

**Subjects array example:** `["chef", "driver", "food", "service"]`

**Auto-labels array example:** `["Complaint Chef", "Food Quality Issue", "Delivery Issue"]`

---

## Design Decisions & Deviations

### 1. Balance Storage (Integer Cents)
**Decision:** Store all monetary values as INTEGER in cents (e.g., $10.99 = 1099 cents).

**Reasoning:** 
- Floating-point arithmetic can cause precision errors (e.g., 0.1 + 0.2 ≠ 0.3)
- Integer arithmetic is exact and deterministic
- Simpler to aggregate and compare
- Division to dollars only needed at presentation layer

### 2. Complaint/Compliment Table Design
**Diagram Ambiguity:** The diagram shows `accountID` and `filer` without clarifying roles.

**Resolution:** Created two distinct columns:
- `about_account_id` - The person the feedback is about (subject)
- `reporter_account_id` - The person filing the feedback (author)

This makes queries like "find all complaints about user X" unambiguous.

### 3. Warnings Lifecycle
**Added columns:**
- `warnings` (INTEGER) - Count of warnings received
- `is_blacklisted` (BOOLEAN) - Explicit blacklist flag

**Business Rule:** Users with warnings >= 3 can be blacklisted by management.

### 4. Transactions Table (Recommended Addition)
**Not in diagram, but essential** for any financial system.

**Purpose:**
- Complete audit trail of all balance changes
- Supports reconciliation and dispute resolution
- Enables financial reporting
- Required for regulatory compliance in many jurisdictions

### 5. Delivery Ratings as Separate Table
**Decision:** Use dedicated `delivery_ratings` table rather than aggregate columns in accounts.

**Reasoning:**
- Maintains complete rating history
- Enables time-based analytics (rating trends)
- Links ratings to specific orders for accountability
- Easier to implement weighted/recent ratings

### 6. JSONB for Opening Hours
**Decision:** Store `opening_hours` as JSONB rather than separate columns.

**Reasoning:**
- Flexible for special hours, holidays, seasonal changes
- Can store exceptions inline
- Easy to extend without migrations
- Works well with modern JSON-capable frontends

---

## Recommended Indices

### Performance-Critical Indices (Migration 002)

| Table | Index | Columns | Type | Reasoning |
|-------|-------|---------|------|-----------|
| accounts | idx_accounts_email | email | BTREE | Login lookups |
| accounts | idx_accounts_type | account_type | BTREE | Filter by role |
| accounts | idx_accounts_restaurant | restaurant_id | BTREE | Employee queries |
| dishes | idx_dishes_restaurant | restaurant_id | BTREE | Menu listings |
| dishes | idx_dishes_name_search | name | GIN (pg_trgm) | ILIKE search |
| dishes | idx_dishes_category | category | BTREE | Category filtering |
| dishes | idx_dishes_rating | average_rating DESC | BTREE | Top-rated queries |
| orders | idx_orders_account | account_id | BTREE | Customer order history |
| orders | idx_orders_status | status | BTREE | Status filtering |
| orders | idx_orders_datetime | order_datetime | BTREE | Date range queries |
| ordered_dishes | idx_ordered_dishes_order | order_id | BTREE | Order details |
| ordered_dishes | idx_ordered_dishes_dish | dish_id | BTREE | Dish popularity |
| bids | idx_bids_order | order_id | BTREE | Bids per order |
| bids | idx_bids_delivery_person | delivery_person_id | BTREE | Driver's bids |
| complaints | idx_complaints_about | about_account_id | BTREE | Complaints about user |
| complaints | idx_complaints_unresolved | is_resolved | BTREE PARTIAL (WHERE FALSE) | Pending complaints |
| transactions | idx_transactions_account | account_id | BTREE | Account history |
| threads | idx_threads_restaurant | restaurant_id | BTREE | Forum threads |
| posts | idx_posts_thread | thread_id | BTREE | Thread posts |

### Index Reasoning by Query Pattern

**1. Dish Search (most common)**
```sql
SELECT * FROM dishes 
WHERE restaurant_id = ? AND name ILIKE '%burger%'
ORDER BY average_rating DESC LIMIT 10;
```
- Uses: idx_dishes_restaurant, idx_dishes_name_search, idx_dishes_rating

**2. Top-Rated Dishes**
```sql
SELECT * FROM dishes 
WHERE restaurant_id = ? 
ORDER BY average_rating DESC, review_count DESC LIMIT 10;
```
- Uses: idx_dishes_restaurant, idx_dishes_rating

**3. Most Popular Dishes (by orders)**
```sql
SELECT d.*, COUNT(od.id) as order_count
FROM dishes d
LEFT JOIN ordered_dishes od ON d.id = od.dish_id
GROUP BY d.id
ORDER BY order_count DESC LIMIT 10;
```
- Uses: idx_ordered_dishes_dish (critical for JOIN performance)

**4. Customer Order History**
```sql
SELECT * FROM orders 
WHERE account_id = ? 
ORDER BY order_datetime DESC LIMIT 20;
```
- Uses: idx_orders_account, idx_orders_datetime

**5. Pending Deliveries**
```sql
SELECT * FROM orders 
WHERE status IN ('ready', 'out_for_delivery')
ORDER BY order_datetime;
```
- Uses: idx_orders_status

---

## Sample Queries

### Top 5 Most Popular Dishes (by order count)
```sql
SELECT 
    d.id,
    d.name,
    d.price,
    d.average_rating,
    COALESCE(SUM(od.quantity), 0) as total_ordered
FROM dishes d
LEFT JOIN ordered_dishes od ON d.id = od.dish_id
GROUP BY d.id
ORDER BY total_ordered DESC
LIMIT 5;
```

### Top 5 Highest-Rated Dishes
```sql
SELECT 
    id,
    name,
    price,
    average_rating,
    review_count
FROM dishes
WHERE review_count >= 5  -- Minimum reviews for significance
ORDER BY average_rating DESC, review_count DESC
LIMIT 5;
```

### Users with 3+ Warnings (Blacklist Candidates)
```sql
SELECT id, email, first_name, last_name, warnings, is_blacklisted
FROM accounts
WHERE warnings >= 3
ORDER BY warnings DESC;
```

### Complaint Resolution Flow
```sql
-- File a complaint
INSERT INTO complaints (about_account_id, reporter_account_id, feedback_type, description)
VALUES (5, 6, 'complaint', 'Late delivery by 30 minutes');

-- Manager resolves it
UPDATE complaints
SET is_resolved = TRUE,
    manager_decision = 'Warning issued to delivery person',
    resolved_by_id = 1,
    resolved_at = NOW()
WHERE id = ?;
```

---

## Migration Commands

### Apply Migrations
```bash
# Using Alembic from backend directory
cd backend
alembic upgrade head

# Or specific migration
alembic upgrade 001_initial_schema
alembic upgrade 002_add_indices
```

### Load Seed Data
```bash
# Connect to database and run seed script
psql -U restaurant_user -d restaurant_db -f sql/seed_data.sql

# Or via Docker
docker-compose exec postgres psql -U restaurant_user -d restaurant_db -f /sql/seed_data.sql
```

### Rollback
```bash
# Rollback one step
alembic downgrade -1

# Rollback to beginning
alembic downgrade base
```
