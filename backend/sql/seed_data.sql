-- =============================================================================
-- DashX Seed Data - Authoritative Schema
-- =============================================================================
-- This script populates the database with demo data for testing and development.
-- Matches the authoritative database schema exactly.
-- 
-- Contents:
--   - 1 Restaurant
--   - 11 Accounts: 1 manager, 2 chefs, 2 delivery, 5 customers (1 VIP)
--   - 5 Dishes
--   - Orders and bids demonstrating relationships
--   - Various balances to test success/failure scenarios
--
-- Run this after applying migrations:
--   psql -U restaurant_user -d restaurant_db -f backend/sql/seed_data.sql
-- =============================================================================

-- Start transaction for atomicity
BEGIN;

-- =============================================================================
-- RESTAURANT
-- =============================================================================
INSERT INTO restaurant (id, name, address)
VALUES (
    1,
    'DashX Bistro',
    '123 Main Street, New York, NY 10001'
);

-- Reset sequence for restaurant
SELECT setval('restaurant_id_seq', 1, true);

-- =============================================================================
-- ACCOUNTS
-- =============================================================================
-- Password hash is bcrypt hash of 'password123' for all test accounts
-- In production, use proper unique passwords!
-- $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi

-- Manager (ID: 1)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    1,
    1,
    'manager@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'manager',
    500000,  -- $5000.00 balance
    7500     -- $75.00/hour wage
);

-- Chef 1 (ID: 2)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    2,
    1,
    'chef.gordon@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'chef',
    250000,  -- $2500.00 balance
    5000     -- $50.00/hour wage
);

-- Chef 2 (ID: 3)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    3,
    1,
    'chef.julia@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'chef',
    180000,  -- $1800.00 balance
    4500     -- $45.00/hour wage
);

-- Delivery Person 1 (ID: 4)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    4,
    1,
    'delivery.mike@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'delivery',
    75000,   -- $750.00 balance
    2000     -- $20.00/hour wage
);

-- Delivery Person 2 (ID: 5)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    5,
    1,
    'delivery.lisa@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    1,        -- Has 1 warning
    'delivery',
    60000,   -- $600.00 balance
    1800     -- $18.00/hour wage
);

-- Customer 1 - VIP (ID: 6)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    6,
    NULL,
    'vip.john@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'vip',
    100000,  -- $1000.00 balance - enough for orders
    NULL
);

-- Customer 2 (ID: 7)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    7,
    NULL,
    'customer.jane@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'customer',
    5000,    -- $50.00 balance - limited funds
    NULL
);

-- Customer 3 (ID: 8)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    8,
    NULL,
    'customer.bob@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'customer',
    25000,   -- $250.00 balance
    NULL
);

-- Customer 4 (ID: 9)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    9,
    NULL,
    'customer.alice@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    2,       -- Has 2 warnings
    'customer',
    150,     -- $1.50 balance - insufficient for most orders (test failure)
    NULL
);

-- Customer 5 (ID: 10)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    10,
    NULL,
    'customer.charlie@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'customer',
    35000,   -- $350.00 balance
    NULL
);

-- Visitor (ID: 11) - browsing only, no orders
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage)
VALUES (
    11,
    NULL,
    'visitor@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    0,
    'visitor',
    0,
    NULL
);

-- Reset sequence for accounts
SELECT setval('"accounts_ID_seq"', 11, true);

-- =============================================================================
-- DISHES
-- =============================================================================
-- 5 dishes with varied costs for testing

-- Dish 1: Signature Burger (by Chef Gordon)
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES (
    1,
    1,
    'DashX Signature Burger',
    'Juicy Angus beef patty with aged cheddar, caramelized onions, lettuce, tomato, and our secret DashX sauce on a brioche bun.',
    1599,  -- $15.99
    '/images/dishes/signature-burger.jpg',
    4.75,
    48,
    2
);

-- Dish 2: Truffle Fries (by Chef Julia)
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES (
    2,
    1,
    'Truffle Parmesan Fries',
    'Crispy golden fries tossed with truffle oil, fresh parmesan, and herbs. A perfect side or snack.',
    899,   -- $8.99
    '/images/dishes/truffle-fries.jpg',
    4.50,
    72,
    3
);

-- Dish 3: Grilled Salmon (by Chef Gordon)
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES (
    3,
    1,
    'Atlantic Grilled Salmon',
    'Fresh Atlantic salmon fillet, grilled to perfection with lemon butter sauce, served with seasonal vegetables and rice pilaf.',
    2499,  -- $24.99
    '/images/dishes/grilled-salmon.jpg',
    4.80,
    35,
    2
);

-- Dish 4: Caesar Salad (by Chef Julia)
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES (
    4,
    1,
    'Classic Caesar Salad',
    'Crisp romaine lettuce, house-made caesar dressing, parmesan crisps, and garlic croutons. Add grilled chicken for $5.',
    1299,  -- $12.99
    '/images/dishes/caesar-salad.jpg',
    4.20,
    55,
    3
);

-- Dish 5: Chocolate Lava Cake (by Chef Julia)
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES (
    5,
    1,
    'Molten Chocolate Lava Cake',
    'Warm chocolate cake with a gooey molten center, served with vanilla ice cream and fresh berries.',
    999,   -- $9.99
    '/images/dishes/chocolate-lava.jpg',
    4.90,
    88,
    3
);

-- Reset sequence for dishes
SELECT setval('dishes_id_seq', 5, true);

-- =============================================================================
-- ORDERS
-- =============================================================================
-- Create sample orders demonstrating various statuses

-- Order 1: VIP customer, delivered (ID: 1)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", note)
VALUES (
    1,
    6,  -- VIP John
    NOW() - INTERVAL '2 days',
    3497,  -- $34.97 total
    'delivered',
    NULL,
    'Please ring doorbell twice'
);

-- Order 2: Regular customer, preparing (ID: 2)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", note)
VALUES (
    2,
    8,  -- Bob
    NOW() - INTERVAL '30 minutes',
    2198,  -- $21.98 total
    'preparing',
    NULL,
    NULL
);

-- Order 3: Customer pickup, ready (ID: 3)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", note)
VALUES (
    3,
    10,  -- Charlie
    NOW() - INTERVAL '20 minutes',
    1299,  -- $12.99 total (no delivery fee)
    'ready',
    NULL,
    NULL
);

-- Order 4: Pending order with bids (ID: 4)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", note)
VALUES (
    4,
    7,  -- Jane (limited funds, but this order is small enough)
    NOW() - INTERVAL '10 minutes',
    1198,  -- $11.98 total
    'pending',
    NULL,
    'Extra napkins please'
);

-- Order 5: Cancelled order (ID: 5)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", note)
VALUES (
    5,
    6,  -- VIP John
    NOW() - INTERVAL '1 day',
    2997,
    'cancelled',
    NULL,
    NULL
);

-- Reset sequence for orders
SELECT setval('orders_id_seq', 5, true);

-- =============================================================================
-- BID
-- =============================================================================
-- Delivery bids for orders

-- Bids for Order 1 (delivered - one accepted)
INSERT INTO bid (id, "deliveryPersonID", "orderID", "bidAmount")
VALUES 
    (1, 4, 1, 499),
    (2, 5, 1, 599);

-- Update Order 1 with accepted bid
UPDATE orders SET "bidID" = 1 WHERE id = 1;

-- Bids for Order 2 (preparing - pending bids)
INSERT INTO bid (id, "deliveryPersonID", "orderID", "bidAmount")
VALUES 
    (3, 4, 2, 399),
    (4, 5, 2, 349);

-- Bids for Order 4 (pending - has competing bids)
INSERT INTO bid (id, "deliveryPersonID", "orderID", "bidAmount")
VALUES 
    (5, 4, 4, 299),
    (6, 5, 4, 279);

-- Reset sequence for bid
SELECT setval('bid_id_seq', 6, true);

-- =============================================================================
-- ORDERED_DISHES (junction table with composite PK)
-- =============================================================================

-- Order 1 items: Signature Burger + Truffle Fries
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (1, 1, 1),  -- 1x Signature Burger
    (2, 1, 1);  -- 1x Truffle Fries

-- Order 2 items: Signature Burger
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (1, 2, 1);  -- 1x Signature Burger

-- Order 3 items: Caesar Salad
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (4, 3, 1);  -- 1x Caesar Salad

-- Order 4 items: Truffle Fries
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (2, 4, 1);  -- 1x Truffle Fries

-- Order 5 items (cancelled): Grilled Salmon + Caesar Salad
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (3, 5, 1),  -- 1x Grilled Salmon
    (4, 5, 1);  -- 1x Caesar Salad (cancelled orders still track what was ordered)

-- =============================================================================
-- DeliveryRating (accountID is PK)
-- =============================================================================

-- Delivery rating for Mike (ID: 4)
INSERT INTO "DeliveryRating" ("accountID", "averageRating", reviews)
VALUES (4, 5.00, 1);

-- Delivery rating for Lisa (ID: 5)
INSERT INTO "DeliveryRating" ("accountID", "averageRating", reviews)
VALUES (5, 4.50, 2);

-- =============================================================================
-- COMPLAINT
-- =============================================================================

-- Compliment for Chef Gordon from VIP John
INSERT INTO complaint (id, "accountID", type, description, filer)
VALUES (1, 2, 'compliment', 'The Signature Burger was cooked to perfection. Chef Gordon is amazing!', 6);

-- Complaint about delivery delay (for testing complaint resolution flow)
INSERT INTO complaint (id, "accountID", type, description, filer)
VALUES (2, 5, 'complaint', 'Delivery was 30 minutes late on my last order.', 9);

-- Reset sequence for complaint
SELECT setval('complaint_id_seq', 2, true);

-- =============================================================================
-- THREAD & POST (Forum)
-- =============================================================================

-- Create a forum thread
INSERT INTO thread (id, topic)
VALUES (
    1,
    'What''s your favorite dish at DashX Bistro?'
);

-- Posts in the thread
INSERT INTO post (id, "threadID", "posterID", title, body)
VALUES 
    (1, 1, 6, 'My top pick', 'I absolutely love the Signature Burger! The secret sauce is to die for.'),
    (2, 1, 7, NULL, 'Haven''t tried the burger yet but the Truffle Fries are incredible!'),
    (3, 1, 8, NULL, 'The Chocolate Lava Cake is hands down the best dessert I''ve ever had.'),
    (4, 1, 6, NULL, 'I need to try that next time! Thanks for the recommendation.');

-- Reset sequences
SELECT setval('thread_id_seq', 1, true);
SELECT setval('post_id_seq', 4, true);

-- =============================================================================
-- AGENT_QUERY & AGENT_ANSWER (AI Chat)
-- =============================================================================

-- Sample AI query
INSERT INTO agent_query (id, "accountID", question)
VALUES (
    1,
    7,
    'What vegetarian options do you have?'
);

-- AI-generated answer
INSERT INTO agent_answer (id, "queryID", answer, "authorID", average_rating, reviews)
VALUES (
    1,
    1,
    'We have several vegetarian options! Our Classic Caesar Salad is a great choice, and our Truffle Parmesan Fries are vegetarian-friendly. We can also modify the Signature Burger to a veggie patty upon request.',
    NULL,  -- AI generated
    4.5,
    2
);

-- Reset sequences
SELECT setval('agent_query_id_seq', 1, true);
SELECT setval('agent_answer_id_seq', 1, true);

-- =============================================================================
-- openRequest (Job Applications)
-- =============================================================================

-- Pending chef application
INSERT INTO "openRequest" (id, email, password)
VALUES (
    1,
    'newchef.applicant@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi'
);

-- Reset sequence
SELECT setval('"openRequest_id_seq"', 1, true);

-- =============================================================================
-- closureRequest (accountID is PK)
-- =============================================================================

-- Sample closure request (pending)
INSERT INTO "closureRequest" ("accountID")
VALUES (11);  -- Visitor guest

-- =============================================================================
-- Commit the transaction
-- =============================================================================
COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- VOICE REPORTS
-- =============================================================================
-- Example voice reports demonstrating different scenarios

-- Voice Report 1: Customer complaint about chef (pending processing)
INSERT INTO voice_reports (
    id, submitter_id, audio_file_path, file_size_bytes, duration_seconds,
    mime_type, status, is_processed, created_at, updated_at
)
VALUES (
    1,
    6,  -- Customer Alice
    'backend/static/voice_reports/voice_6_20251202_complaint_chef.mp3',
    45632,
    18,
    'audio/mpeg',
    'pending',
    false,
    '2025-12-02T09:15:00Z',
    '2025-12-02T09:15:00Z'
);

-- Voice Report 2: VIP compliment about delivery person (analyzed)
INSERT INTO voice_reports (
    id, submitter_id, audio_file_path, file_size_bytes, duration_seconds,
    mime_type, transcription, sentiment, subjects, auto_labels, confidence_score,
    status, is_processed, related_order_id, related_account_id,
    created_at, updated_at
)
VALUES (
    2,
    9,  -- VIP Grace
    'backend/static/voice_reports/voice_9_20251202_compliment_delivery.mp3',
    38421,
    15,
    'audio/mpeg',
    'I just wanted to say the delivery person was excellent today. They arrived exactly on time and were very professional and courteous. The food was still hot and perfectly packaged. Really impressed with the service!',
    'compliment',
    '["driver", "delivery", "service"]'::jsonb,
    '["Compliment Delivery Person", "Excellent Delivery", "Excellent Service"]'::jsonb,
    0.89,
    'analyzed',
    true,
    9,  -- Related to order 9
    5,  -- Delivery person Frank
    '2025-12-01T18:30:00Z',
    '2025-12-01T18:31:00Z'
);

-- Voice Report 3: Customer complaint about late delivery (analyzed, resolved)
INSERT INTO voice_reports (
    id, submitter_id, audio_file_path, file_size_bytes, duration_seconds,
    mime_type, transcription, sentiment, subjects, auto_labels, confidence_score,
    status, is_processed, related_order_id, related_account_id,
    manager_notes, resolved_by, resolved_at, created_at, updated_at
)
VALUES (
    3,
    7,  -- Customer Bob
    'backend/static/voice_reports/voice_7_20251201_complaint_late.mp3',
    52134,
    21,
    'audio/mpeg',
    'My order was over 45 minutes late today. The driver called saying they got lost finding my address, but I provided clear directions. The food arrived cold and I had to reheat everything. Really disappointing experience after waiting so long.',
    'complaint',
    '["driver", "delivery", "food"]'::jsonb,
    '["Complaint Delivery Person", "Delivery Issue", "Food Quality Issue"]'::jsonb,
    0.85,
    'resolved',
    true,
    8,  -- Related to order 8
    4,  -- Delivery person Eve
    'Legitimate complaint. Issued warning to delivery person for navigation issues.',
    1,  -- Resolved by Manager
    '2025-12-01T20:00:00Z',
    '2025-12-01T19:00:00Z',
    '2025-12-01T20:00:00Z'
);

-- Voice Report 4: Delivery person compliment about customer (analyzed)
INSERT INTO voice_reports (
    id, submitter_id, audio_file_path, file_size_bytes, duration_seconds,
    mime_type, transcription, sentiment, subjects, auto_labels, confidence_score,
    status, is_processed, created_at, updated_at
)
VALUES (
    4,
    5,  -- Delivery person Frank
    'backend/static/voice_reports/voice_5_20251202_feedback.mp3',
    29876,
    12,
    'audio/mpeg',
    'Just wanted to provide positive feedback. The customer was very understanding when I was running a few minutes behind. They even helped me with the heavy bags. Really appreciate working with respectful customers.',
    'compliment',
    '["service"]'::jsonb,
    '["General Compliment", "Excellent Service"]'::jsonb,
    0.78,
    'analyzed',
    true,
    '2025-12-02T10:00:00Z',
    '2025-12-02T10:01:00Z'
);

-- Voice Report 5: Customer complaint about food quality (analyzed, needs resolution)
INSERT INTO voice_reports (
    id, submitter_id, audio_file_path, file_size_bytes, duration_seconds,
    mime_type, transcription, sentiment, subjects, auto_labels, confidence_score,
    status, is_processed, related_account_id, created_at, updated_at
)
VALUES (
    5,
    8,  -- Customer Carol
    'backend/static/voice_reports/voice_8_20251202_complaint_food.mp3',
    61234,
    25,
    'audio/mpeg',
    'I need to file a complaint about my recent order. The pasta was severely undercooked and the sauce was cold. This is clearly a kitchen preparation issue. The chef did not follow basic cooking standards. I expect better quality from your restaurant.',
    'complaint',
    '["chef", "food", "kitchen"]'::jsonb,
    '["Complaint Chef", "Food Quality Issue"]'::jsonb,
    0.92,
    'analyzed',
    true,
    2,  -- Chef Bob
    '2025-12-02T11:00:00Z',
    '2025-12-02T11:02:00Z'
);

-- Reset sequence for voice_reports
SELECT setval('voice_reports_id_seq', 5, true);

-- =============================================================================

-- Verify data was inserted correctly
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Check accounts
    SELECT COUNT(*) INTO v_count FROM accounts;
    RAISE NOTICE 'Accounts created: %', v_count;
    
    -- Check dishes
    SELECT COUNT(*) INTO v_count FROM dishes;
    RAISE NOTICE 'Dishes created: %', v_count;
    
    -- Check orders
    SELECT COUNT(*) INTO v_count FROM orders;
    RAISE NOTICE 'Orders created: %', v_count;
    
    -- Check bid
    SELECT COUNT(*) INTO v_count FROM bid;
    RAISE NOTICE 'Bids created: %', v_count;
    
    -- Check voice reports
    SELECT COUNT(*) INTO v_count FROM voice_reports;
    RAISE NOTICE 'Voice reports created: %', v_count;
    
    RAISE NOTICE 'Seed data loaded successfully!';
END $$;
