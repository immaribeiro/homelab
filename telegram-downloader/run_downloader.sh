#!/bin/bash

# Telegram E-book Downloader Script
# Downloads e-books from a specified Telegram channel/group

set -e

# Default values
CHAT_ID="${1:-2152949316}"
GROUP_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --chat-id|-c)
            CHAT_ID="$2"
            shift 2
            ;;
        --group|-g)
            GROUP_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Determine if it's a channel or chat based on the ID format
if [[ "$GROUP_MODE" == true ]] || [[ "$CHAT_ID" =~ ^[0-9]+$ ]]; then
    # If group mode is explicitly set or ID looks like a channel (5 digits)
    if [[ "$GROUP_MODE" == true ]]; then
        TARGET_TYPE="channel"
    else
        # Check if it's a channel by looking at the last 5 digits (channel IDs are typically 5+ digits)
        if [[ ${#CHAT_ID} -ge 5 ]]; then
            TARGET_TYPE="channel"
        else
            TARGET_TYPE="chat"
        fi
    fi
else
    TARGET_TYPE="chat"
fi

# Set environment variables for the downloader_botapi.py script
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"

# Set download directory
DOWNLOAD_DIR="/Users/imma/Downloads/ebook-library/PT"

# Ensure download directory exists
mkdir -p "$DOWNLOAD_DIR"

echo "=========================================="
echo "Telegram E-book Downloader"
echo "=========================================="
echo ""
echo "Target Chat ID: $CHAT_ID"
echo "Type: $TARGET_TYPE"
echo "Download Directory: $DOWNLOAD_DIR"
echo ""

# Check if bot token is set
if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
    echo "[ERROR] TELEGRAM_BOT_TOKEN environment variable is not set!"
    echo "Please set it using: export TELEGRAM_BOT_TOKEN='your_bot_token'"
    exit 1
fi

echo "Starting download..."
echo ""

# Run the bot API downloader with appropriate parameters
if [[ "$TARGET_TYPE" == "channel" ]]; then
    python3 downloader_botapi.py --chat-id "$CHAT_ID" --group
else
    python3 downloader_botapi.py --chat-id "$CHAT_ID"
fi

echo ""
echo "=========================================="
echo "Download completed!"
echo "=========================================="
