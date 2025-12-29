# Optional CI/CD Features Setup Guide

This guide covers setting up the three optional CI/CD features:
1. Codecov (code coverage reporting)
2. Performance benchmarks
3. Email notifications

---

## 1. Codecov Setup (Code Coverage Reporting)

### What It Does
- Tracks code coverage over time
- Shows coverage changes in PRs
- Helps identify untested code

### Setup Steps

1. **Sign up for Codecov** (free for public repos):
   - Go to https://about.codecov.io/
   - Sign in with GitHub
   - Authorize Codecov to access your repositories

2. **Add repository to Codecov**:
   - Once logged in, click "Add repository"
   - Select your `clarion` repository
   - Copy the repository upload token

3. **Add GitHub Secret**:
   - Go to GitHub → Your Repository → **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `CODECOV_TOKEN`
   - Value: Paste the token from Codecov
   - Click **Add secret**

4. **That's it!** The CI workflow will automatically upload coverage on each run.

### Files Created
- `.codecov.yml` - Configuration for Codecov (coverage thresholds, what to ignore)

---

## 2. Performance Benchmarks

### What It Does
- Tracks clustering performance over time
- Ensures performance requirements are met (<100ms incremental assignment, etc.)
- Helps identify performance regressions

### Setup Steps

1. **Already configured!** The benchmark tests are in `tests/benchmark/`

2. **Benchmarks run automatically** on pushes to `main` branch

3. **View results**:
   - Go to GitHub Actions → Your workflow run
   - Download the `benchmark-results` artifact
   - View `benchmark_results.json` for detailed metrics

### Running Benchmarks Locally

```bash
# Install benchmark tool
pip install pytest-benchmark

# Run all benchmarks
pytest tests/benchmark/ -v --benchmark-only

# Compare with previous run
pytest tests/benchmark/ -v --benchmark-only --benchmark-compare
```

### Files Created
- `tests/benchmark/test_clustering_performance.py` - Performance benchmark tests
- `.github/workflows/BENCHMARK_SETUP.md` - Detailed benchmark documentation

---

## 3. Email Notifications

### What It Does
- Sends email when CI fails
- Includes details about which jobs failed
- Link to view full error logs

### Setup Steps

#### Step 1: Create Gmail App Password

1. **Enable 2-Step Verification** (if not already enabled):
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select **Mail** and **Other (Custom name)**
   - Enter "GitHub Actions" as the name
   - Click **Generate**
   - **Copy the 16-character password** (you won't see it again!)

#### Step 2: Add GitHub Secrets

1. Go to GitHub → Your Repository → **Settings** → **Secrets and variables** → **Actions**

2. **Add EMAIL_USERNAME**:
   - Click **New repository secret**
   - Name: `EMAIL_USERNAME`
   - Value: `sgerhart@gmail.com`
   - Click **Add secret**

3. **Add EMAIL_PASSWORD**:
   - Click **New repository secret** again
   - Name: `EMAIL_PASSWORD`
   - Value: `<paste-the-16-character-app-password-from-step-1>`
   - Click **Add secret**

#### Step 3: Test

1. Push a commit that will fail tests (or just wait for a real failure)
2. Check your email (sgerhart@gmail.com) for the notification

### Email Format

**Subject**: `Clarion CI Failed: CI #123`

**Body**: Includes:
- Repository and branch info
- Which jobs failed
- Link to view full error logs

### Files Created
- `.github/workflows/NOTIFICATIONS_SETUP.md` - Detailed notification setup guide

---

## Summary

| Feature | Status | Setup Required | Notes |
|---------|--------|----------------|-------|
| **Codecov** | ✅ Ready | Add `CODECOV_TOKEN` secret | Free for public repos |
| **Benchmarks** | ✅ Ready | None (automatic) | Runs on main branch pushes |
| **Email** | ✅ Ready | Add `EMAIL_USERNAME` + `EMAIL_PASSWORD` secrets | Uses Gmail App Password |

---

## Quick Setup Checklist

- [ ] Sign up for Codecov and add `CODECOV_TOKEN` secret
- [ ] Generate Gmail App Password
- [ ] Add `EMAIL_USERNAME` secret (sgerhart@gmail.com)
- [ ] Add `EMAIL_PASSWORD` secret (Gmail App Password)
- [ ] Test by pushing a commit

---

## Troubleshooting

### Codecov not uploading
- Check that `CODECOV_TOKEN` secret is set correctly
- The workflow won't fail if Codecov is unavailable (it's optional)

### Email not sending
- Verify Gmail App Password is correct (16 characters, no spaces)
- Check that 2-Step Verification is enabled
- Check GitHub Actions logs for SMTP errors

### Benchmarks not running
- Benchmarks only run on pushes to `main` branch (not PRs)
- Check that `tests/benchmark/` directory exists

---

## Disabling Features

If you want to disable any feature:

1. **Codecov**: Remove or don't set `CODECOV_TOKEN` secret
2. **Benchmarks**: Comment out the `performance-benchmark` job in `.github/workflows/ci.yml`
3. **Email**: Remove `EMAIL_USERNAME` and `EMAIL_PASSWORD` secrets, or comment out the `notify` job

