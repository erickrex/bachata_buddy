#!/bin/bash

# Cleanup Secrets Script
# This script helps remove sensitive data from your repository

set -e

echo "🔒 Bachata Buddy - Secret Cleanup Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check current status
echo "📋 Step 1: Checking current repository status..."
echo ""

echo "Files currently tracked by git that contain '.env':"
git ls-files | grep -E "\.env" || echo "  ✅ No .env files are currently tracked"
echo ""

echo "Files in git history that contained secrets:"
echo "  - .env.compute_engine (contains Google API key, DB password, Elasticsearch key)"
echo "  - .env.deployment (needs investigation)"
echo ""

# Step 2: Verify .gitignore
echo "📋 Step 2: Verifying .gitignore..."
if grep -q ".env.compute_engine" .gitignore; then
    echo "  ✅ .gitignore updated to exclude .env.compute_engine"
else
    echo "  ⚠️  .gitignore may need updating"
fi
echo ""

# Step 3: Check for hardcoded secrets in current files
echo "📋 Step 3: Scanning for hardcoded secrets in current files..."
echo ""

echo "Checking for Google API keys (AIza...):"
if git grep -n "AIza[0-9A-Za-z-_]\{35\}" 2>/dev/null | grep -v "your-gemini-api-key-here" | grep -v "SECURITY_AUDIT"; then
    echo "  ❌ Found Google API keys in tracked files!"
else
    echo "  ✅ No Google API keys found in tracked files"
fi
echo ""

echo "Checking for OpenAI API keys (sk-proj-...):"
if git grep -n "sk-proj-" 2>/dev/null | grep -v "your-key-here" | grep -v "YOUR_KEY" | grep -v "\.\.\."; then
    echo "  ❌ Found OpenAI API keys in tracked files!"
else
    echo "  ✅ No OpenAI API keys found in tracked files"
fi
echo ""

# Step 4: Provide cleanup instructions
echo "========================================"
echo "🚨 REQUIRED ACTIONS"
echo "========================================"
echo ""

echo "${RED}1. ROTATE ALL COMPROMISED CREDENTIALS${NC}"
echo ""
echo "   Google API Key:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials"
echo "   - Find key: AIzaSyCjGQ8kE5oAuBC-gOCFOCOt7ZekI9g5Z2Y"
echo "   - Regenerate or delete and create new"
echo "   - Add API restrictions"
echo ""
echo "   OpenAI API Key:"
echo "   - Go to: https://platform.openai.com/api-keys"
echo "   - Revoke key starting with: sk-proj-9TfPqehI7yElBq3v..."
echo "   - Create new API key"
echo ""
echo "   Database Password:"
echo "   - Connect to Cloud SQL: 35.188.209.4"
echo "   - Run: ALTER USER postgres WITH PASSWORD 'new-secure-password';"
echo ""
echo "   Elasticsearch API Key:"
echo "   - Log into Elasticsearch cluster"
echo "   - Revoke exposed key"
echo "   - Generate new key"
echo ""

echo "${YELLOW}2. REMOVE SECRETS FROM GIT HISTORY${NC}"
echo ""
echo "   Option A: Using git-filter-repo (recommended)"
echo "   $ brew install git-filter-repo  # or: pip install git-filter-repo"
echo "   $ git filter-repo --path .env.compute_engine --invert-paths"
echo "   $ git filter-repo --path .env.deployment --invert-paths"
echo "   $ git push origin --force --all"
echo ""
echo "   Option B: Using BFG Repo-Cleaner"
echo "   $ brew install bfg"
echo "   $ bfg --delete-files .env.compute_engine"
echo "   $ git reflog expire --expire=now --all"
echo "   $ git gc --prune=now --aggressive"
echo "   $ git push origin --force --all"
echo ""
echo "   ${RED}WARNING: This rewrites git history. Coordinate with your team!${NC}"
echo ""

echo "${GREEN}3. ENABLE SECURITY FEATURES${NC}"
echo ""
echo "   Install git-secrets:"
echo "   $ brew install git-secrets"
echo "   $ git secrets --install"
echo "   $ git secrets --register-aws"
echo "   $ git secrets --add 'AIza[0-9A-Za-z-_]{35}'"
echo "   $ git secrets --add 'sk-proj-[0-9A-Za-z]{100,}'"
echo ""
echo "   Enable GitHub Secret Scanning:"
echo "   - Go to: Settings → Security → Code security and analysis"
echo "   - Enable 'Secret scanning'"
echo "   - Enable 'Push protection'"
echo ""

echo "========================================"
echo "📝 See SECURITY_AUDIT_FINDINGS.md for full details"
echo "========================================"
