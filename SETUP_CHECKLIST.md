# CI/CD Setup Checklist

## Pre-Push Setup

Before pushing to GitHub, set up these optional features for the best CI/CD experience.

### ✅ Codecov (Code Coverage)

1. Sign up at https://about.codecov.io/ (use GitHub login)
2. Add your `clarion` repository
3. Copy the repository upload token
4. Add GitHub Secret:
   - Go to: Repository → Settings → Secrets and variables → Actions
   - New secret: `CODECOV_TOKEN`
   - Value: Paste token from Codecov

**Status**: [ ] Not set up | [ ] Set up

---

### ✅ Email Notifications (CI Failure Alerts)

1. **Enable 2-Step Verification on Gmail** (if not already):
   - https://myaccount.google.com/security

2. **Generate Gmail App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name: "GitHub Actions"
   - Copy the 16-character password

3. **Add GitHub Secrets**:
   - `EMAIL_USERNAME`: `sgerhart@gmail.com`
   - `EMAIL_PASSWORD`: `<16-character-app-password>`

**Status**: [ ] Not set up | [ ] Set up

---

### ✅ Performance Benchmarks

**No setup required!** Benchmarks run automatically on pushes to `main`.

- Benchmarks are in `tests/benchmark/`
- Results uploaded as artifacts
- Can run locally: `pytest tests/benchmark/ -v --benchmark-only`

**Status**: ✅ Ready (automatic)

---

## Quick Commands

```bash
# Run benchmarks locally
pytest tests/benchmark/ -v --benchmark-only

# Run all tests with coverage
pytest --cov=src/clarion --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## After Setup

Once all secrets are configured:
1. ✅ Push to GitHub
2. ✅ Check Actions tab to see workflows running
3. ✅ Codecov will show coverage on PRs
4. ✅ You'll receive emails on CI failures
5. ✅ Benchmark results available as artifacts

---

## Help

See detailed setup guides:
- `SETUP_OPTIONAL_FEATURES.md` - Complete setup instructions
- `.github/workflows/NOTIFICATIONS_SETUP.md` - Email setup details
- `.github/workflows/BENCHMARK_SETUP.md` - Benchmark documentation
