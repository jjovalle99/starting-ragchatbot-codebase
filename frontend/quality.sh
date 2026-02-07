#!/bin/bash

# Frontend Code Quality Checks
# Run from the frontend/ directory: ./quality.sh
# Or from project root: ./frontend/quality.sh

set -e

# Navigate to frontend directory (works whether called from frontend/ or project root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Frontend Code Quality Checks ==="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

# Run Prettier format check
echo "--- Prettier: Checking formatting ---"
if npx prettier --check . 2>&1; then
    echo "Prettier: All files formatted correctly."
else
    echo ""
    echo "Prettier: Formatting issues found."
    echo "Run 'npm run format' from frontend/ to fix automatically."
    exit 1
fi

echo ""
echo "=== All frontend quality checks passed ==="
