#!/bin/bash

# Test script to verify Telegram credentials (Telethon - phone auth)
# This tests if the API ID and Hash are valid

echo "============================================"
echo "Testing Telegram Credentials (Telethon)"
echo "============================================"

API_ID="${TELEGRAM_API_ID:-}"
API_HASH="${TELEGRAM_API_HASH:-}"

echo ""
echo "Checking environment variables:"
echo "  TELEGRAM_API_ID: ${API_ID}"
echo "  TELEGRAM_API_HASH: ${API_HASH}"
echo ""

# Check if credentials are set
if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
    echo "❌ ERROR: Missing credentials!"
    if [ -z "$API_ID" ]; then
        echo "   - TELEGRAM_API_ID is not set"
    fi
    if [ -z "$API_HASH" ]; then
        echo "   - TELEGRAM_API_HASH is not set"
    fi
    exit 1
fi

echo "✓ Both credentials are present"
echo ""

# Test with Telegram API (my.telegram.org)
echo "Testing credentials against my.telegram.org..."
echo ""

# This is a simple test - in reality you need to register on my.telegram.org
# The API will return the credentials if they're valid and registered

echo "To verify these credentials are working:"
echo ""
echo "1. Visit: https://my.telegram.org/"
echo "2. Login with your phone number"
echo "3. Check if these credentials appear in the 'Get project variables' section:"
echo ""
echo "   API ID: ${API_ID}"
echo "   API Hash: ${API_HASH}"
echo ""

# Try to fetch credentials from Telegram API (this will fail without proper registration)
echo "Attempting API test..."

# Note: You need to register your app on my.telegram.org first
# This curl command will only work if you're registered as a developer

curl -s "https://api.telegram.org/bot${API_ID}/getMe" \
    -H "Content-Type: application/json" 2>/dev/null | jq -r '.ok' || echo "0 (not registered as bot developer)"

echo ""
echo "============================================"
echo "Note: For phone authentication, you MUST:"
echo "1. Register your app at https://my.telegram.org/"
echo "2. Get the API_ID and API_HASH from there"
echo "3. Login to Telegram via your app when running the downloader"
echo "============================================"
