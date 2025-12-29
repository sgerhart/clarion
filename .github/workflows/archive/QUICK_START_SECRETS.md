# Quick Start: Adding Secrets to GitHub

## TL;DR Version

### Codecov Token
1. https://about.codecov.io/ → Sign in → Add repo → Copy token
2. GitHub → Settings → Secrets → `CODECOV_TOKEN` → Paste token

### Gmail App Password  
1. https://myaccount.google.com/apppasswords → Generate → Copy 16-char password
2. GitHub → Settings → Secrets → Add `EMAIL_USERNAME` = `sgerhart@gmail.com`
3. GitHub → Settings → Secrets → Add `EMAIL_PASSWORD` = `<16-char-password>`

---

## Step-by-Step (Visual Guide)

### Codecov Setup

```
1. Visit: https://about.codecov.io/
   └─> Click "Sign in with GitHub"
       └─> Authorize Codecov
           └─> Click "Add a repository"
               └─> Find "clarion" → Enable
                   └─> Copy the "Repository Upload Token"
                       └─> Go to GitHub
```

```
GitHub Repository → Settings → Secrets and variables → Actions
└─> Click "New repository secret"
    └─> Name: CODECOV_TOKEN
        └─> Secret: <paste-token>
            └─> Add secret ✅
```

### Gmail App Password

```
1. Visit: https://myaccount.google.com/apppasswords
   └─> Select "Mail" → "Other (Custom name)"
       └─> Enter "GitHub Actions"
           └─> Generate
               └─> Copy 16-character password (no spaces)
                   └─> Go to GitHub
```

```
GitHub Repository → Settings → Secrets and variables → Actions
└─> Click "New repository secret"
    ├─> Name: EMAIL_USERNAME
    │   Secret: sgerhart@gmail.com
    │   └─> Add secret ✅
    │
    └─> Click "New repository secret" (again)
        ├─> Name: EMAIL_PASSWORD
        │   Secret: <paste-16-char-password>
        │   └─> Add secret ✅
```

---

## Direct Links

**Codecov**:
- Sign up: https://about.codecov.io/
- Dashboard: https://app.codecov.io/gh/sgerhart/clarion (after setup)

**Gmail**:
- App Passwords: https://myaccount.google.com/apppasswords
- Security Settings: https://myaccount.google.com/security

**GitHub**:
- Secrets page: https://github.com/sgerhart/clarion/settings/secrets/actions
- Actions page: https://github.com/sgerhart/clarion/actions

---

## What You'll See

After setup, in GitHub Secrets you'll have:
- ✅ `CODECOV_TOKEN` (repository upload token)
- ✅ `EMAIL_USERNAME` (sgerhart@gmail.com)
- ✅ `EMAIL_PASSWORD` (16-character app password)

All three will have "Updated X minutes ago" timestamps.

---

## Need More Help?

See `GITHUB_SECRETS_SETUP.md` for detailed troubleshooting and explanations.

