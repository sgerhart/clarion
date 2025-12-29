# CI/CD Setup Guide

This guide covers setting up all optional CI/CD features for the Clarion project, including performance benchmarks, email notifications, and GitHub secrets configuration.

---

## Table of Contents

1. [GitHub Secrets Setup](#github-secrets-setup)
2. [Codecov Setup](#codecov-setup)
3. [Email Notifications Setup](#email-notifications-setup)
4. [Performance Benchmarking Setup](#performance-benchmarking-setup)
5. [Quick Start](#quick-start)

---

## GitHub Secrets Setup

### Overview

GitHub Secrets are encrypted environment variables that can be used in GitHub Actions workflows. They're needed for:
- Codecov code coverage reporting
- Email notifications on CI failures

### How to Add Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the name and value
5. Click **Add secret**

**Direct Link**: https://github.com/sgerhart/clarion/settings/secrets/actions

---

## Codecov Setup

### Overview

Codecov provides code coverage reporting and visualization. This helps track test coverage over time.

### Step-by-Step Setup

#### Step 1: Sign Up for Codecov

1. **Go to Codecov**: https://about.codecov.io/
2. **Click "Sign Up"** or "Sign in with GitHub"
3. **Authorize Codecov** to access your GitHub account
4. **You'll be redirected to Codecov dashboard**

#### Step 2: Add Your Repository

1. **In Codecov dashboard**, click **"Add a repository"** or **"Get Started"**
2. **Select GitHub** as your Git provider (if prompted)
3. **Find your `clarion` repository** in the list
4. **Click "Add"** or toggle the switch to enable it
5. **You'll see a token** - this is your repository upload token

#### Step 3: Copy the Token

1. **On the repository page**, look for **"Repository Upload Token"** or **"Repo Token"**
2. **Copy the token** (it looks like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
   - ⚠️ **Save this somewhere temporarily** - you'll need it in a moment

#### Step 4: Add Token as GitHub Secret

1. **Go to GitHub**: https://github.com/sgerhart/clarion/settings/secrets/actions
2. **Click "New repository secret"**
3. **Fill in the form**:
   - **Name**: `CODECOV_TOKEN`
   - **Secret**: Paste the token you copied from Codecov
   - **Click "Add secret"**

#### Verification

After setup:
- Coverage reports will be uploaded automatically after each CI run
- View reports at: https://app.codecov.io/gh/sgerhart/clarion
- Coverage badge will appear in README (if configured)

### Quick Reference

| Secret Name | Value | Where to Get It |
|-------------|-------|-----------------|
| `CODECOV_TOKEN` | Repository token | https://about.codecov.io/ → Add repo → Copy token |

---

## Email Notifications Setup

### Overview

Email notifications are sent when CI pipelines fail. This helps catch issues quickly.

### Step-by-Step Setup

#### Step 1: Enable 2-Step Verification

1. **Go to Google Account**: https://myaccount.google.com/
2. **Click "Security"** (left sidebar)
3. **Find "2-Step Verification"**
4. **If already enabled**: Skip to Step 2
5. **If not enabled**:
   - Click "2-Step Verification"
   - Follow the prompts to enable it
   - You'll need your phone for verification

#### Step 2: Generate App Password

1. **Go to App Passwords**: https://myaccount.google.com/apppasswords
   - Or: Google Account → Security → App passwords

2. **You may be asked to sign in again** (this is normal)

3. **Select app**:
   - Dropdown: **"Mail"**

4. **Select device**:
   - Dropdown: **"Other (Custom name)"**

5. **Enter name**:
   - Type: `GitHub Actions`
   - Click **"Generate"**

6. **Copy the password**:
   - You'll see a 16-character password like: `abcd efgh ijkl mnop`
   - ⚠️ **Copy it now** - you won't see it again!
   - Remove spaces when copying (should be 16 characters: `abcdefghijklmnop`)

#### Step 3: Add GitHub Secrets

1. **Go to GitHub**: https://github.com/sgerhart/clarion/settings/secrets/actions

2. **Add EMAIL_USERNAME**:
   - Click **"New repository secret"**
   - **Name**: `EMAIL_USERNAME`
   - **Secret**: `sgerhart@gmail.com`
   - Click **"Add secret"**

3. **Add EMAIL_PASSWORD**:
   - Click **"New repository secret"** again
   - **Name**: `EMAIL_PASSWORD`
   - **Secret**: Paste the 16-character App Password (no spaces)
   - Click **"Add secret"**

### Notification Behavior

- **When**: Only on CI failures (not on success)
- **To**: sgerhart@gmail.com
- **Subject**: "Clarion CI Failed: [workflow] #[run_number]"
- **Content**: Includes job statuses and link to workflow run

### Quick Reference

| Secret Name | Value | Where to Get It |
|-------------|-------|-----------------|
| `EMAIL_USERNAME` | `sgerhart@gmail.com` | Your email address |
| `EMAIL_PASSWORD` | 16-character app password | https://myaccount.google.com/apppasswords → Generate |

### Disabling Notifications

If you want to disable email notifications, you can:

1. Comment out the `notify` job in `.github/workflows/ci.yml`
2. Or remove the `EMAIL_USERNAME` and `EMAIL_PASSWORD` secrets (the job will fail gracefully)

---

## Performance Benchmarking Setup

### Overview

Performance benchmarks ensure the categorization engine meets performance requirements:
- Sketch building: <10 seconds for 380 endpoints
- Clustering: <5 seconds for 380 endpoints
- Incremental assignment: <100ms per endpoint
- Full pipeline: <30 seconds for enterprise dataset

### Running Benchmarks Locally

```bash
# Install benchmark tool
pip install pytest-benchmark

# Run all benchmarks
pytest tests/benchmark/ -v --benchmark-only

# Run with comparison (vs previous run)
pytest tests/benchmark/ -v --benchmark-only --benchmark-compare

# Run specific benchmark
pytest tests/benchmark/test_clustering_performance.py::test_clustering_performance_small -v --benchmark-only
```

### Benchmark Results

Benchmark results are stored in `benchmark_results.json` and uploaded as GitHub Actions artifacts.

### Adding New Benchmarks

Add new benchmark tests in `tests/benchmark/` with the `@pytest.mark.benchmark` marker:

```python
@pytest.mark.benchmark
def test_my_feature_performance(benchmark):
    def my_function():
        # Code to benchmark
        pass
    
    result = benchmark(my_function)
    assert benchmark.stats['mean'] < TARGET_TIME
```

---

## Quick Start

### TL;DR Version

#### Codecov Token
1. https://about.codecov.io/ → Sign in → Add repo → Copy token
2. GitHub → Settings → Secrets → `CODECOV_TOKEN` → Paste token

#### Gmail App Password  
1. https://myaccount.google.com/apppasswords → Generate → Copy 16-char password
2. GitHub → Settings → Secrets → Add `EMAIL_USERNAME` = `sgerhart@gmail.com`
3. GitHub → Settings → Secrets → Add `EMAIL_PASSWORD` = `<16-char-password>`

---

### Complete Setup Checklist

- [ ] Sign up for Codecov at https://about.codecov.io/
- [ ] Add `clarion` repository in Codecov dashboard
- [ ] Copy Codecov repository upload token
- [ ] Add `CODECOV_TOKEN` secret to GitHub
- [ ] Enable 2-Step Verification on Google Account (if not already)
- [ ] Generate Gmail App Password at https://myaccount.google.com/apppasswords
- [ ] Add `EMAIL_USERNAME` secret to GitHub (`sgerhart@gmail.com`)
- [ ] Add `EMAIL_PASSWORD` secret to GitHub (16-character app password)

---

## Verification

### Check Your Secrets

1. **Go to**: https://github.com/sgerhart/clarion/settings/secrets/actions
2. **You should see 3 secrets**:
   - ✅ `CODECOV_TOKEN`
   - ✅ `EMAIL_USERNAME`
   - ✅ `EMAIL_PASSWORD`

### Test It

1. **Make a small change** and push to GitHub:
   ```bash
   git add .
   git commit -m "Test CI/CD setup"
   git push
   ```

2. **Check GitHub Actions**:
   - Go to: https://github.com/sgerhart/clarion/actions
   - You should see workflows running
   - Codecov will upload coverage
   - If tests fail, you'll get an email

---

## Troubleshooting

### Codecov Issues

**Problem**: Coverage not uploading
- **Check**: Secret name is exactly `CODECOV_TOKEN` (case-sensitive)
- **Check**: Token was copied correctly from Codecov
- **Check**: Repository is enabled in Codecov dashboard

### Email Issues

**Problem**: Emails not sending
- **Check**: 2-Step Verification is enabled on Gmail
- **Check**: App Password is 16 characters (no spaces)
- **Check**: Secret names are exactly `EMAIL_USERNAME` and `EMAIL_PASSWORD`
- **Check**: `EMAIL_USERNAME` value is `sgerhart@gmail.com`

**Problem**: "Invalid credentials" error
- **Solution**: Regenerate the App Password and update the secret

### Can't Find Settings?

**Direct Links**:
- Secrets page: https://github.com/sgerhart/clarion/settings/secrets/actions
- Actions page: https://github.com/sgerhart/clarion/actions
- Repository settings: https://github.com/sgerhart/clarion/settings

---

## Security Notes

- ✅ **App Passwords are secure** - They can be revoked anytime
- ✅ **Secrets are encrypted** - Only GitHub Actions can access them
- ✅ **Secrets are masked** - Never shown in logs or UI
- ✅ **Revoke if compromised** - Delete and regenerate anytime

---

## References

- **Codecov**: https://about.codecov.io/
- **Codecov Dashboard**: https://app.codecov.io/gh/sgerhart/clarion (after setup)
- **Gmail App Passwords**: https://myaccount.google.com/apppasswords
- **GitHub Secrets**: https://github.com/sgerhart/clarion/settings/secrets/actions
- **GitHub Actions**: https://github.com/sgerhart/clarion/actions

