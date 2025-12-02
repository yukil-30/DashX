-- Seed data for knowledge_base table
-- Run this after the migration to populate initial FAQ entries

-- Restaurant hours and contact
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'What are your hours of operation?',
    'We are open Monday through Sunday from 11:00 AM to 10:00 PM. Last orders are taken at 9:30 PM.',
    'hours,open,close,schedule,time,when',
    0.95,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'Where are you located?',
    'We are located at 123 Main Street, Downtown. Free parking is available behind the building.',
    'location,address,where,find,directions,parking',
    0.95,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How can I contact you?',
    'You can reach us by phone at (555) 123-4567, email at info@restaurant.com, or through our website contact form.',
    'contact,phone,email,call,reach',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Ordering and delivery
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'How do I place an order?',
    'You can place an order through our website, mobile app, or by calling us directly. For online orders, simply browse our menu, add items to your cart, and checkout.',
    'order,how,place,buy,purchase',
    0.95,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'Do you offer delivery?',
    'Yes! We offer delivery within a 5-mile radius. Delivery fees vary based on distance. You can also choose from available delivery persons who bid for your order.',
    'delivery,deliver,home,address',
    0.95,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How long does delivery take?',
    'Typical delivery time is 30-45 minutes depending on your location and current order volume. You can see estimated delivery times from each delivery person who bids on your order.',
    'delivery,time,how long,wait,minutes',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'Can I pick up my order?',
    'Yes, you can choose pickup when placing your order. Orders are typically ready within 20-30 minutes. We will send you a notification when your order is ready.',
    'pickup,pick up,collect,takeaway,takeout',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Payment and account
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'What payment methods do you accept?',
    'We accept credit/debit cards, and you can also pre-load your account balance. VIP members get a 10% discount on all orders.',
    'payment,pay,credit,debit,card,methods',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How do I add money to my account?',
    'Log into your account and go to the Deposit section. You can add funds using your credit or debit card. The balance will be available immediately for orders.',
    'deposit,add,money,balance,funds,account',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How do I become a VIP member?',
    'VIP status is automatically granted after you complete a certain number of orders. VIP members enjoy 10% discounts, free delivery credits, and priority support.',
    'VIP,member,membership,benefits,upgrade',
    0.85,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Menu and dietary
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'Do you have vegetarian options?',
    'Yes! We have a wide selection of vegetarian dishes including salads, pasta, and main courses. Look for the (V) symbol on our menu.',
    'vegetarian,vegan,meat-free,plant,diet',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'Are there gluten-free options?',
    'Yes, we offer gluten-free versions of many dishes. Please inform us of any allergies when ordering, and our chef will accommodate your needs.',
    'gluten,gluten-free,celiac,allergy,allergies',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'What are your most popular dishes?',
    'Our top dishes include the Grilled Salmon, Mushroom Risotto, and our signature Chocolate Lava Cake. Check out the ratings on our menu to see customer favorites!',
    'popular,best,favorite,recommend,top,signature',
    0.85,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Orders and issues
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'Can I cancel my order?',
    'You can cancel your order if it has not started preparation. Go to your order details and click Cancel. If preparation has started, please contact us for assistance.',
    'cancel,order,refund,undo',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How do I track my order?',
    'Once your order is confirmed, you can track it in real-time through the Orders section. You will see status updates as your order is prepared and delivered.',
    'track,order,status,where,progress',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'What if there is a problem with my order?',
    'If you have any issues with your order, please file a complaint through the Complaints section or contact us directly. We take all feedback seriously and will resolve issues promptly.',
    'problem,issue,wrong,complaint,help,support',
    0.90,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Delivery person info
INSERT INTO knowledge_base (question, answer, keywords, confidence, author_id, is_active, created_at, updated_at) VALUES
(
    'How do delivery bids work?',
    'When you place an order, delivery persons can bid to deliver it. You can see each bidder''s rating, estimated time, and fee. Choose the one that best fits your needs.',
    'bid,delivery,bidding,choose,select,driver',
    0.85,
    NULL,
    TRUE,
    NOW(),
    NOW()
),
(
    'How do I rate my delivery experience?',
    'After your order is delivered, you can rate the delivery person from 1-5 stars. Your feedback helps us maintain quality service.',
    'rate,rating,review,feedback,delivery,driver',
    0.85,
    NULL,
    TRUE,
    NOW(),
    NOW()
);

-- Verify insertions
SELECT COUNT(*) as total_kb_entries FROM knowledge_base WHERE is_active = TRUE;
