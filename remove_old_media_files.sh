#!/bin/bash

# Remove Old Media Files from Git History
# This script removes all .mp3, .mp4, .wav, .avi, .mov, .webm files
# that were added before commit 476cdd1 (chore: update README, add DEPLOYMENT instructions)

set -e

echo "🎬 Removing Old Media Files from Git History"
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
BACKUP_DIR="../bachata_buddy_backup_media_cleanup_$(date +%Y%m%d_%H%M%S)"
git clone . "$BACKUP_DIR"
echo "  ✅ Backup created at: $BACKUP_DIR"
echo ""

# Show what will be removed
echo "📋 Media files to be removed from history:"
echo "  Total files: 124"
echo "  File types: .mp3, .mp4, .wav, .avi, .mov, .webm"
echo "  Added before commit: 476cdd1 (chore: update README, add DEPLOYMENT instructions)"
echo ""
echo "Sample files:"
head -10 /tmp/old_media_files.txt | sed 's/^/    /'
echo "    ... and 114 more files"
echo ""

# Calculate approximate size savings
echo "📊 Checking repository size..."
BEFORE_SIZE=$(du -sh .git | cut -f1)
echo "  Current size: $BEFORE_SIZE"
echo ""

read -p "Continue with cleanup? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "🔧 Running git-filter-repo to remove old media files..."
echo ""

# Use git-filter-repo with path-based filtering
# We'll remove files by their paths from the list
git filter-repo --invert-paths --paths-from-file /tmp/old_media_files.txt --force

echo ""
echo "✅ Old media files removed from git history!"
echo ""

# Show new size
AFTER_SIZE=$(du -sh .git | cut -f1)
echo "📊 Repository size after cleanup:"
echo "  Before: $BEFORE_SIZE"
echo "  After:  $AFTER_SIZE"
echo ""

echo "========================================"
echo "📋 Next Steps:"
echo "========================================"
echo ""
echo "1. Verify the cleanup:"
echo "   $ git log --all --oneline | head -20"
echo "   $ git log --all --name-only | grep -E '\.(mp3|mp4)$' | head -10"
echo ""
echo "2. Add remote back (git-filter-repo removes it):"
echo "   $ git remote add origin git@github.com:erickrex/bachata_buddy.git"
echo ""
echo "3. Force push to remote (THIS WILL REWRITE HISTORY):"
echo "   $ git push origin --force --all"
echo "   $ git push origin --force --tags"
echo ""
echo "4. Verify on GitHub:"
echo "   - Check that old media files are not in history"
echo "   - Repository size should be significantly smaller"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Backup saved at: $BACKUP_DIR"
echo "   - All team members must re-clone or reset their repos"
echo "   - This is in addition to the previous security cleanup"
echo "========================================"
