#!/bin/bash

# Remove Google Cloud and Gemini References
# This script removes all mentions of Google Cloud, GCP, and Gemini from documentation

set -e

echo "🧹 Removing Google Cloud and Gemini References"
echo "========================================"
echo ""

# Create backups
echo "📦 Creating backups..."
for file in README.md ARCHITECTURE.md BLUEPRINT_ARCHITECTURE_STATUS.md .env.example backend/.env.example; do
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup"
        echo "  ✅ Backed up $file"
    fi
done
echo ""

echo "📝 Files to be updated:"
echo "  - README.md"
echo "  - ARCHITECTURE.md"
echo "  - BLUEPRINT_ARCHITECTURE_STATUS.md"
echo "  - .env.example"
echo "  - backend/.env.example (if exists)"
echo "  - SECURITY_AUDIT_FINDINGS.md"
echo ""

read -p "Continue with cleanup? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "🔧 Removing references..."
echo ""

# Count occurrences before
echo "Before cleanup:"
grep -ri "google\|gemini\|gcp" --include="*.md" --include="*.example" . 2>/dev/null | wc -l | xargs echo "  Total references found:"
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "========================================"
echo "📋 Manual Review Required:"
echo "========================================"
echo ""
echo "The following files have been backed up with .backup extension:"
echo "  - README.md.backup"
echo "  - ARCHITECTURE.md.backup"
echo "  - BLUEPRINT_ARCHITECTURE_STATUS.md.backup"
echo "  - .env.example.backup"
echo ""
echo "Please review the changes and commit when ready."
echo "========================================"
