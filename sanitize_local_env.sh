#!/bin/bash

# Sanitize Local .env Files
# This script removes hardcoded API keys from your local .env files

set -e

echo "🧹 Sanitizing Local .env Files"
echo "========================================"
echo ""

# Backup existing files
echo "Creating backups..."
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "  ✅ Backed up .env to .env.backup"
fi

if [ -f "backend/.env" ]; then
    cp backend/.env backend/.env.backup
    echo "  ✅ Backed up backend/.env to backend/.env.backup"
fi

echo ""
echo "Removing hardcoded API keys..."

# Sanitize root .env
if [ -f ".env" ]; then
    sed -i.tmp 's/^OPENAI_API_KEY=sk-proj-.*/OPENAI_API_KEY=your-openai-api-key-here/' .env
    sed -i.tmp 's/^GOOGLE_API_KEY=AIza.*/GOOGLE_API_KEY=your-gemini-api-key-here/' .env
    rm -f .env.tmp
    echo "  ✅ Sanitized .env"
fi

# Sanitize backend/.env
if [ -f "backend/.env" ]; then
    sed -i.tmp 's/^OPENAI_API_KEY=sk-proj-.*/OPENAI_API_KEY=your-openai-api-key-here/' backend/.env
    sed -i.tmp 's/^GOOGLE_API_KEY=AIza.*/GOOGLE_API_KEY=your-gemini-api-key-here/' backend/.env
    rm -f backend/.env.tmp
    echo "  ✅ Sanitized backend/.env"
fi

echo ""
echo "========================================"
echo "✅ Local .env files sanitized!"
echo ""
echo "Next steps:"
echo "1. Get NEW API keys (old ones are compromised)"
echo "2. Update your local .env files with NEW keys"
echo "3. Never commit .env files to git"
echo ""
echo "Backups saved as:"
echo "  - .env.backup"
echo "  - backend/.env.backup"
echo "========================================"
