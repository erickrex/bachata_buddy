# Security Audit - Hardcoded API Keys Found

## 🚨 CRITICAL FINDINGS

### 1. Google API Key Exposed in Git History
**File:** `.env.compute_engine` (commit `979d78aeaf1804d56152e0fa7cd87c43d2385e50`)
**Key Found:** `AIzaSyCjGQ8kE5oAuBC-gOCFOCOt7ZekI9g5Z2Y`
**Status:** ⚠️ EXPOSED IN PUBLIC REPOSITORY

### 2. OpenAI API Key Hardcoded in Current Files
**Files:** 
- `.env` (root)
- `backend/.env`

**Key Found:** `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`
**Status:** ⚠️ CURRENTLY IN REPOSITORY (but .env should be gitignored)

### 3. Database Password Exposed in Git History
**File:** `.env.compute_engine`
**Password:** `donerick123`
**Database:** Cloud SQL instance at `35.188.209.4`

### 4. Elasticsearch API Key Exposed in Git History
**File:** `.env.compute_engine`
**Key:** `Ul9NcERwb0JkUGE3bnB5cXprSDI6ZjcyTmQnRRSElRakhJUQ==`

---

## 📋 IMMEDIATE ACTION REQUIRED

### Step 1: Rotate ALL Compromised Credentials

#### Google API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Find the key `AIzaSyCjGQ8kE5oAuBC-gOCFOCOt7ZekI9g5Z2Y`
3. Click "Regenerate Key" or delete and create a new one
4. Add API restrictions (HTTP referrers, IP addresses, or API restrictions)
5. Update your local `.env` files with the new key

#### OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Revoke the key starting with `sk-proj-9TfPqehI7yElBq3v...`
3. Create a new API key
4. Update your local `.env` files with the new key

#### Database Password
1. Connect to your Cloud SQL instance
2. Change the password for user `postgres`
```sql
ALTER USER postgres WITH PASSWORD 'new-secure-password-here';
```
3. Update all applications using this database

#### Elasticsearch API Key
1. Log into your Elasticsearch cluster
2. Revoke the exposed API key
3. Generate a new API key
4. Update your configuration

### Step 2: Update .gitignore

Add these patterns to `.gitignore`:
```
# Environment files - ALL variations
.env*
!.env.example
*.env
.env.compute_engine
.env.deployment
```

### Step 3: Remove Sensitive Files from Git History

**WARNING:** This will rewrite git history. Coordinate with your team first.

```bash
# Install git-filter-repo if not already installed
# brew install git-filter-repo  # macOS
# pip install git-filter-repo    # Python

# Remove the sensitive file from all history
git filter-repo --path .env.compute_engine --invert-paths

# Force push to remote (DANGEROUS - coordinate with team)
git push origin --force --all
git push origin --force --tags
```

**Alternative (safer but less thorough):**
Use GitHub's built-in secret scanning removal or BFG Repo-Cleaner.

### Step 4: Verify Current Repository State

```bash
# Check if .env files are tracked
git ls-files | grep -E "\.env"

# Should only show .env.example files, not actual .env files
```

---

## 🔍 CURRENT STATUS

### Files Currently Tracked by Git
- ❌ `.env` (root) - **SHOULD NOT BE TRACKED**
- ❌ `backend/.env` - **SHOULD NOT BE TRACKED**
- ❌ `backend/.env.local` - **SHOULD NOT BE TRACKED**
- ❌ `frontend/.env` - **SHOULD NOT BE TRACKED**
- ❌ `frontend/.env.production` - **SHOULD NOT BE TRACKED**

### Files in Git History (Deleted but Still Accessible)
- ❌ `.env.compute_engine` - Contains Google API key, DB password, Elasticsearch key
- ❌ `.env.deployment` - Unknown contents, needs investigation

---

## ✅ RECOMMENDED SECURITY PRACTICES

### 1. Use Environment-Specific .env Files
```
.env.example          # Template (safe to commit)
.env                  # Local development (NEVER commit)
.env.local            # Local overrides (NEVER commit)
.env.production       # Production (NEVER commit)
```

### 2. Use Secret Management Services
- **AWS:** AWS Secrets Manager or Parameter Store
- **GCP:** Secret Manager
- **Local Development:** Use `.env` files (gitignored)

### 3. Add Pre-commit Hooks
Install `git-secrets` or `detect-secrets`:
```bash
# Install git-secrets
brew install git-secrets

# Set up hooks
git secrets --install
git secrets --register-aws
git secrets --add 'AIza[0-9A-Za-z-_]{35}'  # Google API keys
git secrets --add 'sk-proj-[0-9A-Za-z]{100,}'  # OpenAI keys
```

### 4. Enable GitHub Secret Scanning
- Go to repository Settings → Security → Code security and analysis
- Enable "Secret scanning"
- Enable "Push protection" to prevent future commits with secrets

### 5. Regular Security Audits
```bash
# Scan for secrets in current files
git grep -E "AIza[0-9A-Za-z-_]{35}"
git grep -E "sk-proj-[0-9A-Za-z]{100,}"
git grep -E "password.*=.*['\"][^'\"]{8,}"

# Scan git history
git log -p | grep -E "AIza[0-9A-Za-z-_]{35}"
```

---

## 📝 CHECKLIST

- [ ] Rotate Google API key
- [ ] Rotate OpenAI API key  
- [ ] Change database password
- [ ] Rotate Elasticsearch API key
- [ ] Update `.gitignore` to exclude all `.env*` files
- [ ] Remove `.env` files from git tracking
- [ ] Remove sensitive files from git history
- [ ] Force push cleaned history (coordinate with team)
- [ ] Enable GitHub secret scanning
- [ ] Install pre-commit hooks for secret detection
- [ ] Update all deployment configurations with new credentials
- [ ] Verify no other secrets are exposed
- [ ] Document secret management process for team

---

## 🔗 HELPFUL RESOURCES

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [OpenAI: Best practices for API key safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
- [git-filter-repo documentation](https://github.com/newren/git-filter-repo)
