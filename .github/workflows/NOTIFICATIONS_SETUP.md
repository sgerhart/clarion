# Email Notifications Setup

## Overview

Email notifications are sent when CI pipelines fail. This helps catch issues quickly.

## Configuration

Email notifications use Gmail SMTP. You need to set up GitHub Secrets:

### Required Secrets

1. **EMAIL_USERNAME**: Your Gmail address (e.g., `sgerhart@gmail.com`)
2. **EMAIL_PASSWORD**: Gmail App Password (NOT your regular password)

### Setting Up Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Go to **App passwords**: https://myaccount.google.com/apppasswords
4. Select **Mail** and **Other (Custom name)**
5. Enter "GitHub Actions" as the name
6. Click **Generate**
7. Copy the 16-character password
8. Add it as `EMAIL_PASSWORD` secret in GitHub

### Setting Up GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add:
   - Name: `EMAIL_USERNAME`
   - Value: `sgerhart@gmail.com`
5. Click **New repository secret** again
6. Add:
   - Name: `EMAIL_PASSWORD`
   - Value: `<your-gmail-app-password>`

## Notification Behavior

- **When**: Only on CI failures (not on success)
- **To**: sgerhart@gmail.com
- **Subject**: "Clarion CI Failed: [workflow] #[run_number]"
- **Content**: Includes job statuses and link to workflow run

## Codecov Setup (Optional but Recommended)

Codecov provides code coverage reporting. Set up is optional:

1. Sign up at https://about.codecov.io/
2. Connect your GitHub repository
3. Copy the repository upload token
4. Add as GitHub Secret:
   - Name: `CODECOV_TOKEN`
   - Value: `<your-codecov-token>`

If you don't set up Codecov, the coverage upload will be skipped (it's configured to not fail CI if Codecov is unavailable).

## Disabling Notifications

If you want to disable email notifications, you can:

1. Comment out the `notify` job in `.github/workflows/ci.yml`
2. Or remove the `EMAIL_USERNAME` and `EMAIL_PASSWORD` secrets (the job will fail gracefully)

