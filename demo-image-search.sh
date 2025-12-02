#!/bin/bash
# Image Search Demo Script
# Demonstrates the image search API functionality

set -e

echo "🍽️  DashX Image Search Demo"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Login
echo -e "${BLUE}Step 1: Logging in as customer...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"customer@test.com","password":"password123"}' \
  | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed. Make sure backend is running."
    exit 1
fi

echo -e "${GREEN}✓ Logged in successfully${NC}"
echo ""

# Step 2: Check status
echo -e "${BLUE}Step 2: Checking image search status...${NC}"
STATUS=$(curl -s http://localhost:8000/image-search/status \
  -H "Authorization: Bearer $TOKEN")

echo "$STATUS" | jq '.'
echo ""

# Step 3: Create a test image
echo -e "${BLUE}Step 3: Creating test food image...${NC}"
python3 - <<EOF
from PIL import Image

# Create a simple red square (curry-like color)
img = Image.new('RGB', (200, 200), color='#CC3300')
img.save('/tmp/test_food.jpg', 'JPEG')
print("✓ Test image created at /tmp/test_food.jpg")
EOF

echo ""

# Step 4: Search with the image
echo -e "${BLUE}Step 4: Searching for similar dishes...${NC}"
RESULTS=$(curl -s -X POST http://localhost:8000/image-search \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_food.jpg" \
  -F "top_k=5")

echo "$RESULTS" | jq '.'
echo ""

# Step 5: Show summary
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Demo Complete!${NC}"
echo ""

# Parse and show results
DISH_COUNT=$(echo "$RESULTS" | jq 'length')

if [ "$DISH_COUNT" = "null" ] || [ "$DISH_COUNT" = "0" ]; then
    echo "ℹ️  No dishes found. This is expected if:"
    echo "   - No dishes with images in database"
    echo "   - Running in fresh test environment"
    echo ""
    echo "To see results:"
    echo "   1. Add dishes with images to database"
    echo "   2. Run: curl -X POST http://localhost:8000/image-search/precompute \\"
    echo "            -H \"Authorization: Bearer $TOKEN\""
    echo "   3. Re-run this demo"
else
    echo "✓ Found $DISH_COUNT matching dishes!"
    echo ""
    echo "Top matches:"
    echo "$RESULTS" | jq -r '.[] | "  • \(.name) - $\(.cost/100) (similarity: \(.similarity_score // 0))"'
fi

echo ""
echo "🔗 Try the web UI:"
echo "   http://localhost:3000/image-search"
echo ""

# Cleanup
rm -f /tmp/test_food.jpg
