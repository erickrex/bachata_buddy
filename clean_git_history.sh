#!/bin/bash

# Clean Git History - Remove Sensitive Files
# This script removes .env.compute_engine and .env.deployment from git history

set -e

echo "🧹 Cleaning Git History"
echo "========================================"
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    echo "Please commit or stash your changes first"
    exit 1
fi

# Create a backup
echo "📦 Creating backup..."
BACKUP_DIR="../bachata_buddy_backup_$(date +%Y%m%d_%H%M%S)"
git clone . "$BACKUP_DIR"
echo "  ✅ Backup created at: $BACKUP_DIR"
echo ""

# Show what will be removed
echo "📋 Files to be removed from history:"
echo "  - .env.compute_engine (contains Google API key, DB password, Elasticsearch key)"
echo "  - .env.deployment (may contain sensitive data)"
echo ""

read -p "Continue with cleanup? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "🔧 Running git-filter-repo..."
echo ""

# Remove the sensitive files from all history
git filter-repo --invert-paths \
    --path .env.compute_engine \
    --path .env.deployment \
    --force

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "========================================"
echo "📋 Next Steps:"
echo "========================================"
echo ""
echo "1. Verify the cleanup:"
echo "   $ git log --all --oneline | head -20"
echo "   $ git log --all -- .env.compute_engine  # Should show nothing"
echo ""
echo "2. Force push to remote (THIS WILL REWRITE HISTORY):"
echo "   $ git remote add origin <your-repo-url>  # If needed"
echo "   $ git push origin --force --all"
echo "   $ git push origin --force --tags"
echo ""
echo "3. Notify team members:"
echo "   - They need to re-clone the repository"
echo "   - Or run: git fetch origin && git reset --hard origin/main"
echo ""
echo "4. Verify on GitHub:"
echo "   - Check that .env.compute_engine is not in history"
echo "   - GitHub may take time to update their cache"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Backup saved at: $BACKUP_DIR"
echo "   - All team members must re-clone or reset their repos"
echo "   - Rotate all exposed credentials immediately"
echo "========================================"
