# Quick Reference - Security Cleanup

## ✅ Status: Git History Cleaned, Push Pending

## 🚀 What You Need to Do NOW

### 1. Force Push (Choose One Method)

**Method A: SSH (Recommended)**
```bash
git remote set-url origin git@github.com:erickrex/bachata_buddy.git
git push origin --force --all
git push origin --force --tags
```

**Method B: HTTPS with Timeouts**
```bash
git config http.postBuffer 524288000
git push origin --force --all
git push origin --force --tags
```

### 2. Rotate Credentials (CRITICAL!)

| Service | Action | URL |
|---------|--------|-----|
| Google API | Delete `AIzaSyCjGQ8kE5oAuBC-gOCFOCOt7ZekI9g5Z2Y` | https://console.cloud.google.com/apis/credentials |
| OpenAI | Revoke `sk-proj-9TfPqehI7yElBq3v...` | https://platform.openai.com/api-keys |
| Database | Change password for `postgres@35.188.209.4` | `ALTER USER postgres WITH PASSWORD 'new';` |
| Elasticsearch | Revoke exposed key | Your Elasticsearch console |

### 3. Enable Security

```bash
brew install git-secrets
git secrets --install
git secrets --add 'AIza[0-9A-Za-z-_]{35}'
git secrets --add 'sk-proj-[0-9A-Za-z]{100,}'
```

GitHub: Settings → Security → Enable "Secret scanning" + "Push protection"

## 📚 Documentation

- **MANUAL_FORCE_PUSH_GUIDE.md** - Detailed push instructions
- **FINAL_SUMMARY.md** - Complete overview
- **SECURITY_AUDIT_FINDINGS.md** - Full security audit

## 🆘 Troubleshooting

**Push fails with timeout?**
→ Use SSH method or better network

**Files still visible on GitHub?**
→ Wait 15 minutes for cache to clear

**Need to restore?**
→ Backup at: `../bachata_buddy_backup_20251205_153652/`

## ✅ Checklist

- [ ] Force push completed
- [ ] Verified on GitHub
- [ ] Rotated Google API key
- [ ] Rotated OpenAI API key
- [ ] Changed DB password
- [ ] Rotated Elasticsearch key
- [ ] Installed git-secrets
- [ ] Enabled GitHub scanning
- [ ] Updated local .env files
- [ ] Tested application

## 🎯 Priority Order

1. **Force push** (removes secrets from public repo)
2. **Rotate credentials** (invalidates exposed keys)
3. **Enable security** (prevents future leaks)
