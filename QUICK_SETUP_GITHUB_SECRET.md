# Quick Setup: Add FRED API Key to GitHub

You already have a FRED API key! Now just add it to GitHub so the automation can use it.

## Your FRED API Key

```
49b1572b41eb306d5cb567b78bff268a
```

## Step-by-Step Instructions

### 1. Go to GitHub Repository Settings

Visit: https://github.com/NixVir/NixVir.github.io/settings/secrets/actions

Or manually navigate:
1. Go to https://github.com/NixVir/NixVir.github.io
2. Click **"Settings"** tab (top right)
3. Click **"Secrets and variables"** → **"Actions"** (left sidebar)

### 2. Add New Secret

1. Click the green **"New repository secret"** button

2. Fill in the form:
   - **Name**: `FRED_API_KEY` (exactly as written)
   - **Secret**: `49b1572b41eb306d5cb567b78bff268a`

3. Click **"Add secret"**

### 3. Enable GitHub Actions

1. Go to: https://github.com/NixVir/NixVir.github.io/actions

2. If you see a message about workflows:
   - Click **"I understand my workflows, go ahead and enable them"**

3. You should now see the **"Update Economic Dashboard"** workflow listed

### 4. Test the Automation (Optional)

1. On the Actions page, click **"Update Economic Dashboard"**

2. Click **"Run workflow"** dropdown (right side)

3. Click the green **"Run workflow"** button

4. Wait 1-2 minutes for it to complete

5. Click on the workflow run to see the results

6. Check your dashboard: https://confident-jang-4183f9.netlify.app/dashboard/

## What Happens Next

Once you add the API key:

- ✅ **Automatic daily updates** start immediately
- ✅ Runs every weekday at 9 AM EST
- ✅ Fresh economic data without manual work
- ✅ Dashboard always shows latest information

## Verify It's Working

After the first run:
1. Visit: https://confident-jang-4183f9.netlify.app/dashboard/
2. Check the "Last updated" timestamp
3. Should show current date/time
4. Market data should be from latest trading day

## Security Note

✅ API keys stored as GitHub Secrets are encrypted
✅ Never visible in logs or code
✅ Only accessible to GitHub Actions
✅ .Renviron file is already in .gitignore (safe)

---

**That's it!** The automation is ready to run as soon as you add the secret.

**Total time**: 2-3 minutes
