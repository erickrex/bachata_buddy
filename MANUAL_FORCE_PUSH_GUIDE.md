# Manual Force Push Guide

## 🚨 Network Timeout Issue

The automated force push encountered a network timeout due to the large repository size (870+ MB). This is common with large repositories and can be resolved with the following approaches.

## ✅ Current Status

- ✅ Git history cleaned (sensitive files removed)
- ✅ Backup created at: `../bachata_buddy_backup_20251205_153652/`
- ✅ All documentation updated
- ⏳ Force push pending (needs manual completion)

## 🔧 Solution Options

### Option 1: Use SSH Instead of HTTPS (Recommended)

SSH is more reliable for large pushes:

```bash
# Check current remote
git remote -v

# If using HTTPS, switch to SSH
git remote set-url origin git@github.com:erickrex/bachata_buddy.git

# Verify SSH key is set up
ssh -T git@github.com

# Force push with SSH
git push origin --force --all
git push origin --force --tags
```

### Option 2: Increase Git Timeouts and Retry

```bash
# Increase buffer and timeout settings
git config http.postBuffer 524288000
git config http.lowSpeedLimit 0
git config http.lowSpeedTime 999999

# Try force push again
git push origin --force --all
git push origin --force --tags
```

### Option 3: Push from Better Network

If you're on WiFi, try:
- Switching to Ethernet connection
- Using a different network with better upload speed
- Using a VPN if your ISP throttles GitHub uploads

### Option 4: Use GitHub CLI

```bash
# Install GitHub CLI if not already installed
brew install gh

# Authenticate
gh auth login

# Force push
git push origin --force --all
git push origin --force --tags
```

### Option 5: Reduce Repository Size First

The repository is 870+ MB. You can reduce it by removing large files:

```bash
# Find large files
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | \
  sort --numeric-sort --key=2 | \
  tail -20

# If you find unnecessary large files, remove them:
# git filter-repo --path-glob '*.large-file-pattern' --invert-paths

# Then try pushing again
git push origin --force --all
```

## 📋 Step-by-Step Instructions

### Step 1: Choose Your Approach

I recommend **Option 1 (SSH)** as it's most reliable for large repositories.

### Step 2: Execute the Force Push

```bash
# Using SSH (recommended)
git remote set-url origin git@github.com:erickrex/bachata_buddy.git
git push origin --force --all
git push origin --force --tags

# OR using HTTPS with increased timeouts
git config http.postBuffer 524288000
git push origin --force --all
git push origin --force --tags
```

### Step 3: Verify on GitHub

1. Go to: https://github.com/erickrex/bachata_buddy
2. Check recent commits
3. Try to access old commits with `.env.compute_engine`
4. Verify they return 404

### Step 4: Check GitHub's Cache

GitHub may cache the old history for 10-15 minutes. If you still see the sensitive files:

```bash
# Wait 15 minutes, then check again
# Or contact GitHub Support to request cache invalidation
```

## 🔐 After Successful Push

Once the force push succeeds, immediately:

### 1. Rotate All Credentials

**Google API Key:**
```
https://console.cloud.google.com/apis/credentials
Delete: AIzaSyCjGQ8kE5oAuBC-gOCFOCOt7ZekI9g5Z2Y
```

**OpenAI API Key:**
```
https://platform.openai.com/api-keys
Revoke: sk-proj-9TfPqehI7yElBq3v...
Create new key
```

**Database Password:**
```sql
-- Connect to: 35.188.209.4
ALTER USER postgres WITH PASSWORD 'new-secure-password';
```

**Elasticsearch API Key:**
```
Log into cluster
Revoke exposed key
Generate new key
```

### 2. Enable Security Features

```bash
# Install git-secrets
brew install git-secrets
git secrets --install
git secrets --add 'AIza[0-9A-Za-z-_]{35}'
git secrets --add 'sk-proj-[0-9A-Za-z]{100,}'

# Enable GitHub Secret Scanning
# Go to: Settings → Security → Enable "Secret scanning"
```

### 3. Update Local Environment

```bash
# Update your .env files with NEW credentials
# Never commit .env files again!
```

## 🆘 Troubleshooting

### Error: "RPC failed; HTTP 408"
- **Cause:** Network timeout
- **Solution:** Use SSH (Option 1) or better network (Option 3)

### Error: "fatal: the remote end hung up unexpectedly"
- **Cause:** Repository too large for single push
- **Solution:** Use SSH or increase timeouts

### Error: "Everything up-to-date"
- **Cause:** Remote already has these commits
- **Solution:** This might mean the push actually succeeded! Check GitHub.

### Files Still Visible on GitHub After Push
- **Cause:** GitHub's cache hasn't cleared yet
- **Solution:** Wait 15 minutes, or contact GitHub Support

## 📞 Need Help?

If you continue to have issues:

1. **Check the backup:** `../bachata_buddy_backup_20251205_153652/`
2. **Try SSH method:** Most reliable for large repos
3. **Contact GitHub Support:** They can help with cache invalidation
4. **Alternative:** Create a fresh repository and push the cleaned history there

## ✅ Success Checklist

- [ ] Force push completed successfully
- [ ] Verified on GitHub that `.env.compute_engine` is gone
- [ ] Rotated Google API key
- [ ] Rotated OpenAI API key
- [ ] Changed database password
- [ ] Rotated Elasticsearch API key
- [ ] Installed git-secrets
- [ ] Enabled GitHub secret scanning
- [ ] Updated local .env files
- [ ] Tested application with new credentials

## 🎯 Current Command to Run

**Try this first (SSH method):**

```bash
git remote set-url origin git@github.com:erickrex/bachata_buddy.git
git push origin --force --all
git push origin --force --tags
```

**If that fails, try HTTPS with timeouts:**

```bash
git remote set-url origin https://github.com/erickrex/bachata_buddy.git
git config http.postBuffer 524288000
git config http.lowSpeedLimit 0
git config http.lowSpeedTime 999999
git push origin --force --all
git push origin --force --tags
```

Good luck! The hard part (cleaning the history) is done. Now it's just about getting it pushed to GitHub.
