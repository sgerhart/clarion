# Step-by-Step Guide: Adding GitHub Secrets

This guide walks you through adding the Codecov token and Gmail App Password as GitHub Secrets.

---

## Part 1: Codecov Setup

### Step 1: Sign Up for Codecov

1. **Go to Codecov**: https://about.codecov.io/
2. **Click "Sign Up"** or "Sign in with GitHub"
3. **Authorize Codecov** to access your GitHub account
4. **You'll be redirected to Codecov dashboard**

### Step 2: Add Your Repository

1. **In Codecov dashboard**, click **"Add a repository"** or **"Get Started"**
2. **Select GitHub** as your Git provider (if prompted)
3. **Find your `clarion` repository** in the list
4. **Click "Add"** or toggle the switch to enable it
5. **You'll see a token** - this is your repository upload token

### Step 3: Copy the Token

1. **On the repository page**, look for **"Repository Upload Token"** or **"Repo Token"**
2. **Copy the token** (it looks like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
   - ⚠️ **Save this somewhere temporarily** - you'll need it in a moment

### Step 4: Add Token as GitHub Secret

1. **Open a new tab** and go to your GitHub repository:
   ```
   https://github.com/sgerhart/clarion
   ```

2. **Click on "Settings"** (top menu bar, right side)

3. **In the left sidebar**, scroll down and click:
   ```
   Secrets and variables → Actions
   ```

4. **Click "New repository secret"** button (top right)

5. **Fill in the form**:
   - **Name**: `CODECOV_TOKEN`
   - **Secret**: Paste the token you copied from Codecov
   - **Click "Add secret"**

6. **Done!** ✅ Codecov is now configured

---

## Part 2: Gmail App Password Setup

### Step 1: Enable 2-Step Verification

1. **Go to Google Account**: https://myaccount.google.com/
2. **Click "Security"** (left sidebar)
3. **Find "2-Step Verification"**
4. **If already enabled**: Skip to Step 2
5. **If not enabled**:
   - Click "2-Step Verification"
   - Follow the prompts to enable it
   - You'll need your phone for verification

### Step 2: Generate App Password

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

### Step 3: Add GitHub Secrets

1. **Go back to GitHub**: https://github.com/sgerhart/clarion/settings/secrets/actions

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

4. **Done!** ✅ Email notifications are now configured

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

## Quick Reference

| Secret Name | Value | Where to Get It |
|-------------|-------|-----------------|
| `CODECOV_TOKEN` | Repository token | https://about.codecov.io/ → Add repo → Copy token |
| `EMAIL_USERNAME` | `sgerhart@gmail.com` | Your email address |
| `EMAIL_PASSWORD` | 16-character app password | https://myaccount.google.com/apppasswords → Generate |

---

## Security Notes

- ✅ **App Passwords are secure** - They can be revoked anytime
- ✅ **Secrets are encrypted** - Only GitHub Actions can access them
- ✅ **Secrets are masked** - Never shown in logs or UI
- ✅ **Revoke if compromised** - Delete and regenerate anytime

---

## Next Steps

After setting up secrets:
1. ✅ Push your code to GitHub
2. ✅ Watch workflows run in Actions tab
3. ✅ Check Codecov dashboard for coverage reports
4. ✅ Test email by intentionally failing a test (or wait for a real failure)

