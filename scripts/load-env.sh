#!/usr/bin/env bash
# Load environment variables from .env file and export them
# Usage: source scripts/load-env.sh

set -a  # automatically export all variables
if [ -f .env ]; then
    source .env
    echo "✓ Loaded environment variables from .env"
else
    echo "⚠ .env file not found. Copy .env.example to .env and fill in your values"
    exit 1
fi
set +a
