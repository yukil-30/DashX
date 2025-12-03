-- Full Stack Seed Data for Verification Tests
-- Creates a complete test environment with all user types, dishes, orders, and relationships

BEGIN;

-- Clear existing data (in dependency order)
TRUNCATE TABLE transactions, audit_log, chat_log, voice_reports, 
    ordered_dishes, bid, orders, complaint, "DeliveryRating",
    post, thread, agent_answer, agent_query,
    dishes, "openRequest", "closureRequest", blacklist,
    manager_notifications, knowledge_base, accounts, restaurant CASCADE;

-- Reset sequences
ALTER SEQUENCE restaurant_id_seq RESTART WITH 1;
ALTER SEQUENCE "accounts_ID_seq" RESTART WITH 1;
ALTER SEQUENCE dishes_id_seq RESTART WITH 1;
ALTER SEQUENCE orders_id_seq RESTART WITH 1;
ALTER SEQUENCE bid_id_seq RESTART WITH 1;

-- Insert restaurant (only has id, name, address)
INSERT INTO restaurant (id, name, address)
VALUES (
    1,
    'DashX Test Restaurant',
    '123 Test Street, Test City, TC 12345'
);

-- Insert test accounts
-- 1. Manager (ID=1)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted)
VALUES (1, 1, 'manager@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'manager', 0, 5000, 0, 0, 0, false, false);

-- 2-3. Chefs (ID=2,3)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted)
VALUES 
    (2, 1, 'chef1@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'chef', 0, 2500, 0, 0, 0, false, false),
    (3, 1, 'chef2@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'chef', 0, 2500, 0, 0, 0, false, false);

-- 4-5. Delivery Personnel (ID=4,5)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted)
VALUES 
    (4, 1, 'delivery1@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'delivery', 0, 1500, 0, 0, 0, false, false),
    (5, 1, 'delivery2@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'delivery', 0, 1500, 0, 0, 0, false, false);

-- 6-10. Customers (ID=6-10, one VIP)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted)
VALUES 
    (6, NULL, 'customer1@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'customer', 10000, NULL, 0, 0, 0, false, false),
    (7, NULL, 'customer2@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'customer', 5000, NULL, 0, 0, 0, false, false),
    (8, NULL, 'vip1@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'vip', 20000, NULL, 2, 5, 0, false, false),
    (9, NULL, 'customer3@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'customer', 3000, NULL, 0, 0, 0, false, false),
    (10, NULL, 'visitor1@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 0, 'visitor', 0, NULL, 0, 0, 0, false, false);

-- 11. Customer with warnings (for blacklist testing)
INSERT INTO accounts ("ID", "restaurantID", email, password, warnings, type, balance, wage, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted)
VALUES (11, NULL, 'warned_customer@test.com', '$2b$12$GQ.rUX0lE3v4JygnfubldOU2dlkAfivEKun5MrEoj9.pk7UiUSP5C', 3, 'customer', 5000, NULL, 0, 0, 0, false, false);

-- Reset account sequence
ALTER SEQUENCE "accounts_ID_seq" RESTART WITH 12;

-- Insert delivery ratings
INSERT INTO "DeliveryRating" ("accountID", "averageRating", reviews, total_deliveries, on_time_deliveries, avg_delivery_minutes)
VALUES 
    (4, 4.50, 10, 15, 12, 25),
    (5, 4.20, 8, 10, 8, 30);

-- Insert dishes
INSERT INTO dishes (id, "restaurantID", name, description, cost, picture, average_rating, reviews, "chefID")
VALUES 
    (1, 1, 'Classic Burger', 'Juicy beef burger with lettuce, tomato, onion', 1299, '/static/images/burger.jpg', 4.50, 20, 2),
    (2, 1, 'Margherita Pizza', 'Fresh mozzarella, tomato sauce, basil', 1499, '/static/images/pizza.jpg', 4.80, 35, 2),
    (3, 1, 'Caesar Salad', 'Romaine lettuce, parmesan, croutons, Caesar dressing', 899, '/static/images/salad.jpg', 4.20, 15, 3),
    (4, 1, 'Spaghetti Carbonara', 'Pasta with bacon, eggs, parmesan', 1399, '/static/images/pasta.jpg', 4.70, 28, 3),
    (5, 1, 'Chocolate Lava Cake', 'Warm chocolate cake with molten center', 699, '/static/images/cake.jpg', 4.90, 42, 2);

ALTER SEQUENCE dishes_id_seq RESTART WITH 6;

-- Insert sample orders (for VIP customer history)
INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, "bidID", delivery_address, delivery_fee, subtotal_cents, discount_cents, free_delivery_used)
VALUES 
    (1, 8, '2024-11-15T12:30:00Z', 2598, 'delivered', NULL, '456 VIP Street', 300, 2598, 0, 0),
    (2, 8, '2024-11-20T18:45:00Z', 3497, 'delivered', NULL, '456 VIP Street', 300, 3497, 0, 0),
    (3, 8, '2024-11-25T19:00:00Z', 2698, 'delivered', NULL, '456 VIP Street', 300, 2698, 0, 0);

ALTER SEQUENCE orders_id_seq RESTART WITH 4;

-- Insert ordered dishes for historical orders
INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
VALUES 
    (1, 1, 2),  -- 2 burgers
    (5, 2, 5),  -- 5 cakes
    (2, 3, 2);  -- 2 pizzas

-- Insert knowledge base entries
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at)
VALUES 
    ('What are your opening hours?', 'We are open Monday-Thursday 9am-10pm, Friday 9am-11pm, Saturday 10am-11pm, and Sunday 10am-9pm.', 'hours,open,time,when', 0.95, 1, true, NOW(), NOW()),
    ('Do you deliver?', 'Yes, we offer delivery service with competitive bidding from our delivery partners.', 'deliver,delivery,shipping', 0.90, 1, true, NOW(), NOW()),
    ('How do I become VIP?', 'You can become a VIP by completing 3 orders or spending over $100 total. VIP members get 5% off and free delivery credits.', 'vip,premium,upgrade,membership', 0.92, 1, true, NOW(), NOW()),
    ('What is your refund policy?', 'We offer full refunds for orders cancelled before preparation begins. Partial refunds may be available for issues during delivery.', 'refund,cancel,money back', 0.88, 1, true, NOW(), NOW());

COMMIT;

-- Password for all test accounts: "testpass123"
-- The hash above is bcrypt hash of "testpass123"
