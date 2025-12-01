-- =============================================================================
-- DashX Schema Smoke Tests (SQL Version)
-- =============================================================================
-- Run this script with: psql -U restaurant_user -d restaurant_db -f backend/sql/smoke_tests.sql
-- 
-- These tests verify:
-- 1. Basic table accessibility
-- 2. FK constraint enforcement
-- 3. Sample queries work correctly
-- 4. Seed data integrity
--
-- Expected: All tests should pass (no errors)
-- =============================================================================

\echo '=============================================='
\echo 'DashX Schema Smoke Tests'
\echo '=============================================='
\echo ''

-- =============================================================================
-- TEST 1: Verify tables exist and are accessible
-- =============================================================================
\echo 'TEST 1: Table accessibility'
\echo '--------------------------'

SELECT 'restaurant' as table_name, COUNT(*) as row_count FROM restaurant
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'dishes', COUNT(*) FROM dishes
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'ordered_dishes', COUNT(*) FROM ordered_dishes
UNION ALL
SELECT 'bids', COUNT(*) FROM bids
UNION ALL
SELECT 'complaints', COUNT(*) FROM complaints
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
ORDER BY table_name;

\echo ''
\echo 'PASS: All tables accessible'
\echo ''

-- =============================================================================
-- TEST 2: Verify FK constraint - attempt invalid insert
-- =============================================================================
\echo 'TEST 2: FK Constraint Test (ordered_dishes with non-existent order)'
\echo '-------------------------------------------------------------------'

-- This should FAIL with FK violation error
\echo 'Attempting to insert ordered_dish with non-existent order_id 999999...'
\echo '(Expected: ERROR - violates foreign key constraint)'

DO $$
BEGIN
    INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
    VALUES (999999, 1, 1, 1000);
    RAISE EXCEPTION 'TEST FAILED: FK constraint did not prevent invalid insert';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: FK constraint correctly prevented invalid insert';
END $$;

\echo ''

-- =============================================================================
-- TEST 3: Verify unique email constraint
-- =============================================================================
\echo 'TEST 3: Unique Email Constraint'
\echo '--------------------------------'

DO $$
DECLARE
    existing_email VARCHAR;
BEGIN
    -- Get an existing email
    SELECT email INTO existing_email FROM accounts LIMIT 1;
    
    -- Try to insert duplicate
    INSERT INTO accounts (email, password_hash, account_type)
    VALUES (existing_email, 'hash123', 'customer');
    
    RAISE EXCEPTION 'TEST FAILED: Unique constraint did not prevent duplicate email';
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Unique constraint correctly prevented duplicate email';
END $$;

\echo ''

-- =============================================================================
-- TEST 4: Top 5 Most Popular Dishes (by order count)
-- =============================================================================
\echo 'TEST 4: Top 5 Most Popular Dishes (by order count)'
\echo '---------------------------------------------------'

SELECT 
    d.id,
    d.name,
    d.price / 100.0 as price_dollars,
    d.average_rating,
    COALESCE(SUM(od.quantity), 0) as total_ordered
FROM dishes d
LEFT JOIN ordered_dishes od ON d.id = od.dish_id
GROUP BY d.id
ORDER BY total_ordered DESC
LIMIT 5;

\echo ''

-- =============================================================================
-- TEST 5: Top 5 Highest-Rated Dishes
-- =============================================================================
\echo 'TEST 5: Top 5 Highest-Rated Dishes'
\echo '-----------------------------------'

SELECT 
    id,
    name,
    average_rating,
    review_count
FROM dishes
ORDER BY average_rating DESC, review_count DESC
LIMIT 5;

\echo ''

-- =============================================================================
-- TEST 6: Users with 3+ warnings (should be empty in seed data)
-- =============================================================================
\echo 'TEST 6: Users with 3+ Warnings'
\echo '-------------------------------'

SELECT id, email, first_name, last_name, warnings, is_blacklisted
FROM accounts
WHERE warnings >= 3;

\echo '(Should return 0 rows from seed data)'
\echo ''

-- =============================================================================
-- TEST 7: Verify VIP customer exists with balance
-- =============================================================================
\echo 'TEST 7: VIP Customers'
\echo '---------------------'

SELECT 
    id, 
    email, 
    first_name || ' ' || last_name as full_name,
    balance / 100.0 as balance_dollars,
    free_delivery_credits
FROM accounts 
WHERE account_type = 'vip';

\echo ''

-- =============================================================================
-- TEST 8: Order with items (join test)
-- =============================================================================
\echo 'TEST 8: Sample Order Details'
\echo '----------------------------'

SELECT 
    o.id as order_id,
    a.first_name || ' ' || a.last_name as customer,
    o.status,
    o.final_cost / 100.0 as total_dollars,
    d.name as dish_name,
    od.quantity,
    od.unit_price / 100.0 as unit_price_dollars
FROM orders o
JOIN accounts a ON o.account_id = a.id
JOIN ordered_dishes od ON o.id = od.order_id
JOIN dishes d ON od.dish_id = d.id
WHERE o.status = 'delivered'
LIMIT 5;

\echo ''

-- =============================================================================
-- TEST 9: Bid competition for an order
-- =============================================================================
\echo 'TEST 9: Bids on Orders'
\echo '----------------------'

SELECT 
    o.id as order_id,
    o.status as order_status,
    b.id as bid_id,
    a.first_name || ' ' || a.last_name as delivery_person,
    b.bid_amount / 100.0 as bid_dollars,
    b.status as bid_status
FROM orders o
JOIN bids b ON o.id = b.order_id
JOIN accounts a ON b.delivery_person_id = a.id
ORDER BY o.id, b.bid_amount
LIMIT 10;

\echo ''

-- =============================================================================
-- TEST 10: Complaint Resolution Flow
-- =============================================================================
\echo 'TEST 10: Complaint Resolution Flow Test'
\echo '----------------------------------------'

DO $$
DECLARE
    complaint_id INTEGER;
    manager_id INTEGER;
BEGIN
    -- Get manager ID
    SELECT id INTO manager_id FROM accounts WHERE account_type = 'manager' LIMIT 1;
    
    -- Create test complaint
    INSERT INTO complaints (about_account_id, reporter_account_id, feedback_type, description)
    SELECT 
        (SELECT id FROM accounts WHERE account_type = 'delivery' LIMIT 1),
        (SELECT id FROM accounts WHERE account_type = 'customer' LIMIT 1),
        'complaint',
        'Smoke test complaint - will be deleted'
    RETURNING id INTO complaint_id;
    
    RAISE NOTICE 'Created complaint ID: %', complaint_id;
    
    -- Resolve it
    UPDATE complaints 
    SET is_resolved = TRUE,
        manager_decision = 'Resolved during smoke test',
        resolved_by_id = manager_id,
        resolved_at = NOW()
    WHERE id = complaint_id;
    
    RAISE NOTICE 'Resolved complaint';
    
    -- Verify and cleanup
    DELETE FROM complaints WHERE id = complaint_id;
    
    RAISE NOTICE 'PASS: Complaint flow completed successfully';
END $$;

\echo ''

-- =============================================================================
-- TEST 11: Transaction audit trail
-- =============================================================================
\echo 'TEST 11: Transaction Audit Trail'
\echo '---------------------------------'

SELECT 
    t.id,
    a.email,
    t.transaction_type,
    t.amount / 100.0 as amount_dollars,
    t.balance_before / 100.0 as before_dollars,
    t.balance_after / 100.0 as after_dollars,
    t.description
FROM transactions t
JOIN accounts a ON t.account_id = a.id
ORDER BY t.created_at
LIMIT 5;

\echo ''

-- =============================================================================
-- TEST 12: Check constraint - negative price (should fail)
-- =============================================================================
\echo 'TEST 12: Check Constraint (negative price)'
\echo '-------------------------------------------'

DO $$
BEGIN
    INSERT INTO dishes (restaurant_id, name, price)
    VALUES (1, 'Negative Test', -100);
    
    RAISE EXCEPTION 'TEST FAILED: Check constraint did not prevent negative price';
EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'PASS: Check constraint correctly prevented negative price';
END $$;

\echo ''

-- =============================================================================
-- SUMMARY
-- =============================================================================
\echo '=============================================='
\echo 'SMOKE TESTS COMPLETED'
\echo '=============================================='
\echo ''
\echo 'All tests should show PASS or return expected data.'
\echo 'If any test shows FAILED, investigate the schema.'
\echo ''
