-- =============================================================================
-- DashX Seed Data
-- =============================================================================
-- This script populates the database with demo data for testing and development.
-- 
-- Contents:
--   - 1 Restaurant
--   - 11 Accounts: 1 manager, 2 chefs, 2 delivery, 5 customers (1 VIP)
--   - 5 Dishes with images
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
INSERT INTO restaurant (id, name, address, phone, email, description, opening_hours, is_active)
VALUES (
    1,
    'DashX Bistro',
    '123 Main Street, New York, NY 10001',
    '(212) 555-0100',
    'contact@dashxbistro.com',
    'A modern AI-powered restaurant serving delicious fusion cuisine with fast delivery.',
    '{"monday": {"open": "11:00", "close": "22:00"}, 
      "tuesday": {"open": "11:00", "close": "22:00"}, 
      "wednesday": {"open": "11:00", "close": "22:00"}, 
      "thursday": {"open": "11:00", "close": "22:00"}, 
      "friday": {"open": "11:00", "close": "23:00"}, 
      "saturday": {"open": "10:00", "close": "23:00"}, 
      "sunday": {"open": "10:00", "close": "21:00"}}'::jsonb,
    TRUE
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
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, account_type, balance, wage, warnings)
VALUES (
    1,
    1,
    'manager@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Sarah',
    'Manager',
    '(212) 555-0101',
    'manager',
    500000,  -- $5000.00 balance
    7500,    -- $75.00/hour wage
    0
);

-- Chef 1 (ID: 2)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, account_type, balance, wage, warnings)
VALUES (
    2,
    1,
    'chef.gordon@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Gordon',
    'Ramsay',
    '(212) 555-0102',
    'chef',
    250000,  -- $2500.00 balance
    5000,    -- $50.00/hour wage
    0
);

-- Chef 2 (ID: 3)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, account_type, balance, wage, warnings)
VALUES (
    3,
    1,
    'chef.julia@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Julia',
    'Child',
    '(212) 555-0103',
    'chef',
    180000,  -- $1800.00 balance
    4500,    -- $45.00/hour wage
    0
);

-- Delivery Person 1 (ID: 4)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, account_type, balance, wage, warnings)
VALUES (
    4,
    1,
    'delivery.mike@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Mike',
    'Speedy',
    '(212) 555-0104',
    'delivery',
    75000,   -- $750.00 balance
    2000,    -- $20.00/hour wage
    0
);

-- Delivery Person 2 (ID: 5)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, account_type, balance, wage, warnings)
VALUES (
    5,
    1,
    'delivery.lisa@dashxbistro.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Lisa',
    'Swift',
    '(212) 555-0105',
    'delivery',
    60000,   -- $600.00 balance
    1800,    -- $18.00/hour wage
    1        -- Has 1 warning
);

-- Customer 1 - VIP (ID: 6)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, address, account_type, balance, warnings, free_delivery_credits)
VALUES (
    6,
    NULL,
    'vip.john@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'John',
    'VIPCustomer',
    '(212) 555-1001',
    '456 Park Avenue, Apt 10A, New York, NY 10022',
    'vip',
    100000,  -- $1000.00 balance - enough for orders
    0,
    5        -- 5 free delivery credits
);

-- Customer 2 (ID: 7)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, address, account_type, balance, warnings)
VALUES (
    7,
    NULL,
    'customer.jane@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Jane',
    'Doe',
    '(212) 555-1002',
    '789 Broadway, New York, NY 10003',
    'customer',
    5000,    -- $50.00 balance - limited funds
    0
);

-- Customer 3 (ID: 8)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, address, account_type, balance, warnings)
VALUES (
    8,
    NULL,
    'customer.bob@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Bob',
    'Smith',
    '(212) 555-1003',
    '321 5th Avenue, New York, NY 10016',
    'customer',
    25000,   -- $250.00 balance
    0
);

-- Customer 4 (ID: 9)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, address, account_type, balance, warnings)
VALUES (
    9,
    NULL,
    'customer.alice@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Alice',
    'Johnson',
    '(212) 555-1004',
    '555 Lexington Ave, New York, NY 10017',
    'customer',
    150,     -- $1.50 balance - insufficient for most orders (test failure)
    2        -- Has 2 warnings
);

-- Customer 5 (ID: 10)
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, phone, address, account_type, balance, warnings)
VALUES (
    10,
    NULL,
    'customer.charlie@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Charlie',
    'Brown',
    '(212) 555-1005',
    '999 Madison Ave, New York, NY 10021',
    'customer',
    35000,   -- $350.00 balance
    0
);

-- Visitor (ID: 11) - browsing only, no orders
INSERT INTO accounts (id, restaurant_id, email, password_hash, first_name, last_name, account_type, balance, warnings)
VALUES (
    11,
    NULL,
    'visitor@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'Visitor',
    'Guest',
    'visitor',
    0,
    0
);

-- Reset sequence for accounts
SELECT setval('accounts_id_seq', 11, true);

-- =============================================================================
-- DISHES
-- =============================================================================
-- 5 dishes with varied prices for testing

-- Dish 1: Signature Burger (by Chef Gordon)
INSERT INTO dishes (id, restaurant_id, chef_id, name, description, price, picture, category, is_available, is_special, average_rating, review_count)
VALUES (
    1,
    1,
    2,
    'DashX Signature Burger',
    'Juicy Angus beef patty with aged cheddar, caramelized onions, lettuce, tomato, and our secret DashX sauce on a brioche bun.',
    1599,  -- $15.99
    '/images/dishes/signature-burger.jpg',
    'main',
    TRUE,
    TRUE,
    4.75,
    48
);

-- Dish 2: Truffle Fries (by Chef Julia)
INSERT INTO dishes (id, restaurant_id, chef_id, name, description, price, picture, category, is_available, is_special, average_rating, review_count)
VALUES (
    2,
    1,
    3,
    'Truffle Parmesan Fries',
    'Crispy golden fries tossed with truffle oil, fresh parmesan, and herbs. A perfect side or snack.',
    899,   -- $8.99
    '/images/dishes/truffle-fries.jpg',
    'appetizer',
    TRUE,
    FALSE,
    4.50,
    72
);

-- Dish 3: Grilled Salmon (by Chef Gordon)
INSERT INTO dishes (id, restaurant_id, chef_id, name, description, price, picture, category, is_available, is_special, average_rating, review_count)
VALUES (
    3,
    1,
    2,
    'Atlantic Grilled Salmon',
    'Fresh Atlantic salmon fillet, grilled to perfection with lemon butter sauce, served with seasonal vegetables and rice pilaf.',
    2499,  -- $24.99
    '/images/dishes/grilled-salmon.jpg',
    'main',
    TRUE,
    FALSE,
    4.80,
    35
);

-- Dish 4: Caesar Salad (by Chef Julia)
INSERT INTO dishes (id, restaurant_id, chef_id, name, description, price, picture, category, is_available, is_special, average_rating, review_count)
VALUES (
    4,
    1,
    3,
    'Classic Caesar Salad',
    'Crisp romaine lettuce, house-made caesar dressing, parmesan crisps, and garlic croutons. Add grilled chicken for $5.',
    1299,  -- $12.99
    '/images/dishes/caesar-salad.jpg',
    'appetizer',
    TRUE,
    FALSE,
    4.20,
    55
);

-- Dish 5: Chocolate Lava Cake (by Chef Julia)
INSERT INTO dishes (id, restaurant_id, chef_id, name, description, price, picture, category, is_available, is_special, average_rating, review_count)
VALUES (
    5,
    1,
    3,
    'Molten Chocolate Lava Cake',
    'Warm chocolate cake with a gooey molten center, served with vanilla ice cream and fresh berries.',
    999,   -- $9.99
    '/images/dishes/chocolate-lava.jpg',
    'dessert',
    TRUE,
    TRUE,
    4.90,
    88
);

-- Reset sequence for dishes
SELECT setval('dishes_id_seq', 5, true);

-- =============================================================================
-- ORDERS
-- =============================================================================
-- Create sample orders demonstrating various statuses

-- Order 1: VIP customer, delivered (ID: 1)
INSERT INTO orders (id, account_id, restaurant_id, order_datetime, final_cost, subtotal, delivery_fee, tip, status, delivery_address, note, is_delivery, delivered_at)
VALUES (
    1,
    6,  -- VIP John
    1,
    NOW() - INTERVAL '2 days',
    3497,  -- $34.97 total
    2498,  -- $24.98 subtotal
    499,   -- $4.99 delivery
    500,   -- $5.00 tip
    'delivered',
    '456 Park Avenue, Apt 10A, New York, NY 10022',
    'Please ring doorbell twice',
    TRUE,
    NOW() - INTERVAL '2 days' + INTERVAL '45 minutes'
);

-- Order 2: Regular customer, preparing (ID: 2)
INSERT INTO orders (id, account_id, restaurant_id, order_datetime, final_cost, subtotal, delivery_fee, tip, status, delivery_address, is_delivery, estimated_ready_time)
VALUES (
    2,
    8,  -- Bob
    1,
    NOW() - INTERVAL '30 minutes',
    2198,  -- $21.98 total
    1599,  -- $15.99 subtotal  
    299,   -- $2.99 delivery
    300,   -- $3.00 tip
    'preparing',
    '321 5th Avenue, New York, NY 10016',
    TRUE,
    NOW() + INTERVAL '15 minutes'
);

-- Order 3: Customer pickup, ready (ID: 3)
INSERT INTO orders (id, account_id, restaurant_id, order_datetime, final_cost, subtotal, delivery_fee, tip, status, is_delivery, actual_ready_time)
VALUES (
    3,
    10,  -- Charlie
    1,
    NOW() - INTERVAL '20 minutes',
    1299,  -- $12.99 total (no delivery fee)
    1299,
    0,
    0,
    'ready',
    FALSE,  -- Pickup order
    NOW() - INTERVAL '5 minutes'
);

-- Order 4: Pending order with bids (ID: 4)
INSERT INTO orders (id, account_id, restaurant_id, order_datetime, final_cost, subtotal, delivery_fee, tip, status, delivery_address, note, is_delivery)
VALUES (
    4,
    7,  -- Jane (limited funds, but this order is small enough)
    1,
    NOW() - INTERVAL '10 minutes',
    1198,  -- $11.98 total
    899,   -- $8.99 subtotal
    299,   -- $2.99 delivery
    0,
    'pending',
    '789 Broadway, New York, NY 10003',
    'Extra napkins please',
    TRUE
);

-- Order 5: Cancelled order (ID: 5)
INSERT INTO orders (id, account_id, restaurant_id, order_datetime, final_cost, subtotal, delivery_fee, tip, status, delivery_address, is_delivery)
VALUES (
    5,
    6,  -- VIP John
    1,
    NOW() - INTERVAL '1 day',
    2997,
    2498,
    499,
    0,
    'cancelled',
    '456 Park Avenue, Apt 10A, New York, NY 10022',
    TRUE
);

-- Reset sequence for orders
SELECT setval('orders_id_seq', 5, true);

-- =============================================================================
-- ORDERED_DISHES (junction table)
-- =============================================================================

-- Order 1 items: Signature Burger + Truffle Fries
INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
VALUES 
    (1, 1, 1, 1599),  -- 1x Signature Burger
    (1, 2, 1, 899);   -- 1x Truffle Fries

-- Order 2 items: Signature Burger
INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
VALUES 
    (2, 1, 1, 1599);  -- 1x Signature Burger

-- Order 3 items: Caesar Salad
INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
VALUES 
    (3, 4, 1, 1299);  -- 1x Caesar Salad

-- Order 4 items: Truffle Fries
INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
VALUES 
    (4, 2, 1, 899);   -- 1x Truffle Fries

-- Order 5 items (cancelled): Grilled Salmon + Caesar Salad
INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
VALUES 
    (5, 3, 1, 2499),  -- 1x Grilled Salmon
    (5, 4, 1, 1299);  -- 1x Caesar Salad (cancelled orders still track what was ordered)

-- =============================================================================
-- BIDS
-- =============================================================================
-- Delivery bids for orders

-- Bids for Order 1 (delivered - one accepted)
INSERT INTO bids (id, order_id, delivery_person_id, bid_amount, status, created_at)
VALUES 
    (1, 1, 4, 499, 'accepted', NOW() - INTERVAL '2 days'),
    (2, 1, 5, 599, 'rejected', NOW() - INTERVAL '2 days');

-- Update Order 1 with accepted bid
UPDATE orders SET accepted_bid_id = 1 WHERE id = 1;

-- Bids for Order 2 (preparing - pending bids)
INSERT INTO bids (id, order_id, delivery_person_id, bid_amount, status, created_at)
VALUES 
    (3, 2, 4, 399, 'pending', NOW() - INTERVAL '25 minutes'),
    (4, 2, 5, 349, 'pending', NOW() - INTERVAL '20 minutes');

-- Bids for Order 4 (pending - has competing bids)
INSERT INTO bids (id, order_id, delivery_person_id, bid_amount, status, created_at)
VALUES 
    (5, 4, 4, 299, 'pending', NOW() - INTERVAL '8 minutes'),
    (6, 4, 5, 279, 'pending', NOW() - INTERVAL '5 minutes');

-- Reset sequence for bids
SELECT setval('bids_id_seq', 6, true);

-- =============================================================================
-- TRANSACTIONS (Financial Audit Trail)
-- =============================================================================

-- VIP John initial deposit
INSERT INTO transactions (account_id, transaction_type, amount, balance_before, balance_after, description)
VALUES (6, 'deposit', 100000, 0, 100000, 'Initial account funding');

-- VIP John pays for Order 1
INSERT INTO transactions (account_id, order_id, transaction_type, amount, balance_before, balance_after, description)
VALUES (6, 1, 'order_payment', -3497, 100000, 96503, 'Payment for order #1');

-- Customer Bob deposit
INSERT INTO transactions (account_id, transaction_type, amount, balance_before, balance_after, description)
VALUES (8, 'deposit', 25000, 0, 25000, 'Initial account funding');

-- Customer Bob pays for Order 2
INSERT INTO transactions (account_id, order_id, transaction_type, amount, balance_before, balance_after, description)
VALUES (8, 2, 'order_payment', -2198, 25000, 22802, 'Payment for order #2');

-- =============================================================================
-- DELIVERY_RATINGS
-- =============================================================================

-- Rating for delivery person Mike on Order 1
INSERT INTO delivery_ratings (delivery_person_id, order_id, rater_id, rating, comment)
VALUES (4, 1, 6, 5, 'Super fast delivery, very polite!');

-- =============================================================================
-- DISH_REVIEWS
-- =============================================================================

-- Reviews from VIP John
INSERT INTO dish_reviews (dish_id, account_id, order_id, rating, review_text)
VALUES 
    (1, 6, 1, 5, 'Best burger in town! The secret sauce is amazing.'),
    (2, 6, 1, 4, 'Truffle fries were crispy and flavorful. Would order again.');

-- =============================================================================
-- COMPLAINTS/COMPLIMENTS
-- =============================================================================

-- Compliment for Chef Gordon from VIP John
INSERT INTO complaints (about_account_id, reporter_account_id, order_id, feedback_type, description, is_resolved)
VALUES (2, 6, 1, 'compliment', 'The Signature Burger was cooked to perfection. Chef Gordon is amazing!', TRUE);

-- Complaint about delivery delay (for testing complaint resolution flow)
INSERT INTO complaints (about_account_id, reporter_account_id, order_id, feedback_type, description, is_resolved, manager_decision, resolved_by_id, resolved_at)
VALUES (
    5,  -- About Lisa (delivery)
    9,  -- From Alice
    NULL,
    'complaint',
    'Delivery was 30 minutes late on my last order.',
    TRUE,
    'Warning issued to delivery person. Customer offered a discount on next order.',
    1,  -- Resolved by manager Sarah
    NOW() - INTERVAL '1 hour'
);

-- =============================================================================
-- THREADS & POSTS (Forum)
-- =============================================================================

-- Create a forum thread
INSERT INTO threads (id, restaurant_id, topic, created_by_id, is_pinned)
VALUES (
    1,
    1,
    'What''s your favorite dish at DashX Bistro?',
    6,  -- VIP John
    TRUE
);

-- Posts in the thread
INSERT INTO posts (id, thread_id, poster_id, title, body)
VALUES 
    (1, 1, 6, 'My top pick', 'I absolutely love the Signature Burger! The secret sauce is to die for.'),
    (2, 1, 7, NULL, 'Haven''t tried the burger yet but the Truffle Fries are incredible!'),
    (3, 1, 8, NULL, 'The Chocolate Lava Cake is hands down the best dessert I''ve ever had.');

-- Reply to a post
INSERT INTO posts (id, thread_id, poster_id, parent_post_id, body)
VALUES (4, 1, 6, 3, 'I need to try that next time! Thanks for the recommendation.');

-- Reset sequences
SELECT setval('threads_id_seq', 1, true);
SELECT setval('posts_id_seq', 4, true);

-- =============================================================================
-- AGENT_QUERIES & ANSWERS (AI Chat)
-- =============================================================================

-- Sample AI query
INSERT INTO agent_queries (id, account_id, restaurant_id, question, context)
VALUES (
    1,
    7,
    1,
    'What vegetarian options do you have?',
    '{"dietary_preference": "vegetarian"}'::jsonb
);

-- AI-generated answer
INSERT INTO agent_answers (id, query_id, author_id, answer, is_ai_generated, average_rating, review_count)
VALUES (
    1,
    1,
    NULL,  -- AI generated
    'We have several vegetarian options! Our Classic Caesar Salad is a great choice, and our Truffle Parmesan Fries are vegetarian-friendly. We can also modify the Signature Burger to a veggie patty upon request.',
    TRUE,
    4.5,
    2
);

-- Reset sequences
SELECT setval('agent_queries_id_seq', 1, true);
SELECT setval('agent_answers_id_seq', 1, true);

-- =============================================================================
-- OPEN_REQUESTS (Job Applications)
-- =============================================================================

-- Pending chef application
INSERT INTO open_requests (id, restaurant_id, email, password_hash, first_name, last_name, phone, requested_role, cover_letter, status)
VALUES (
    1,
    1,
    'newchef.applicant@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.KQfQU3Vr6Y8AAi',
    'New',
    'Chef',
    '(212) 555-9999',
    'chef',
    'I have 10 years of culinary experience and would love to join your team.',
    'pending'
);

-- Reset sequence
SELECT setval('open_requests_id_seq', 1, true);

-- =============================================================================
-- CLOSURE_REQUESTS
-- =============================================================================

-- Sample closure request (pending)
INSERT INTO closure_requests (id, account_id, reason, status)
VALUES (
    1,
    11,  -- Visitor guest
    'No longer need the account, just browsing.',
    'pending'
);

-- Reset sequence
SELECT setval('closure_requests_id_seq', 1, true);

-- =============================================================================
-- VIP_HISTORY
-- =============================================================================

-- Record of John becoming VIP
INSERT INTO vip_history (account_id, previous_type, new_type, reason, changed_by_id)
VALUES (
    6,
    'customer',
    'vip',
    'Promoted to VIP after 10 orders with 5-star ratings',
    1  -- By manager
);

-- =============================================================================
-- Commit the transaction
-- =============================================================================
COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES
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
    
    -- Check bids
    SELECT COUNT(*) INTO v_count FROM bids;
    RAISE NOTICE 'Bids created: %', v_count;
    
    RAISE NOTICE 'Seed data loaded successfully!';
END $$;
