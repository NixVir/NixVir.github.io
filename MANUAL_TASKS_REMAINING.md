# Manual Tasks Remaining

## Overview
Most tasks have been completed automatically. The following require manual intervention due to system limitations.

---

## 🔴 Task 1: Close 9 Obsolete Dependabot PRs

### Why Manual?
- GitHub CLI installation requires admin rights on Windows
- GitHub authentication requires browser interaction
- These PRs need to be closed via GitHub website or authenticated CLI

### Method A: GitHub Web Interface (Easiest - 5 minutes)

1. Visit https://github.com/NixVir/NixVir.github.io/pulls

2. For each of these 9 PRs, click on it and close:
   - **PR #17**: Bump decode-uri-component from 0.2.0 to 0.2.2
   - **PR #16**: Bump loader-utils and webpack
   - **PR #14**: Bump async from 2.6.1 to 2.6.4
   - **PR #13**: Bump path-parse from 1.0.5 to 1.0.7
   - **PR #12**: Bump hosted-git-info from 2.7.1 to 2.8.9
   - **PR #11**: Bump lodash from 4.17.15 to 4.17.21
   - **PR #10**: Bump y18n from 3.2.1 to 3.2.2
   - **PR #9**: Bump elliptic from 6.4.1 to 6.5.4
   - **PR #6**: Bump jquery from 3.4.0 to 3.5.0

3. Click "Close pull request"

4. Add this comment:
   ```
   Closing as obsolete - theme updated to newer version (Hugo 0.128.0) which no longer uses npm build dependencies. The /themes/gohugo-theme-ananke/src/ directory targeted by this PR does not exist in the current theme version.
   ```

### Method B: GitHub CLI (If You Want to Automate)

If you install GitHub CLI with admin rights:

1. Install GitHub CLI:
   - Download from: https://cli.github.com/
   - Or use: `choco install gh` (in admin PowerShell)

2. Authenticate:
   ```bash
   gh auth login
   ```

3. Run the provided script:
   ```bash
   bash close_dependabot_prs.sh
   ```

---

## 🟡 Task 2: Optimize Large Image File

### The Issue
- **File**: `static/images/BoulderCOVID-031620.png`
- **Current**: 8.9 MB (too large for web)
- **Target**: ~500 KB
- **Automated scripts failed** due to file encoding/corruption issues

### Solution: Use Online Tool (Easiest - 2 minutes)

**Option 1: TinyPNG** (Recommended)
1. Visit https://tinypng.com/
2. Upload `static/images/BoulderCOVID-031620.png`
3. Download optimized version
4. Replace original file
5. Commit change:
   ```bash
   git add static/images/BoulderCOVID-031620.png
   git commit -m "Optimize BoulderCOVID image (8.9 MB → ~500 KB)"
   git push
   ```

**Option 2: Squoosh** (More Control)
1. Visit https://squoosh.app/
2. Upload image
3. Settings:
   - Resize: 1920px width
   - Format: JPEG
   - Quality: 85
4. Download and replace

**Option 3: GIMP** (If you have it installed)
- See [IMAGE_OPTIMIZATION_GUIDE.md](IMAGE_OPTIMIZATION_GUIDE.md) for detailed instructions

### Alternative: Remove Image
Since this image is only used in an archived COVID-19 post from 2020, you could also:
1. Delete the file
2. Update or remove the reference in the archived post
3. Free up 8.9 MB

---

## ✅ Task 3: Verify Favicon (No Action Needed)

Favicon has been created and configured automatically:
- ✅ `static/favicon.ico` created
- ✅ Multi-size PNGs created
- ✅ Apple touch icon created
- ✅ `config.toml` updated

**To verify it works:**
1. Wait for Netlify to rebuild (automatic after push)
2. Visit https://confident-jang-4183f9.netlify.app/
3. Check browser tab for NixVir favicon

---

## 📊 Progress Summary

| Task | Status | Automated | Manual Effort |
|------|--------|-----------|---------------|
| Close 9 PRs | ⚠️ Pending | ❌ | 5 minutes |
| Optimize image | ⚠️ Pending | ❌ | 2 minutes |
| Create favicon | ✅ Done | ✅ | - |
| Update config | ✅ Done | ✅ | - |
| Documentation | ✅ Done | ✅ | - |

**Total Manual Effort Required**: ~7 minutes

---

## Quick Reference Links

- **GitHub Pull Requests**: https://github.com/NixVir/NixVir.github.io/pulls
- **TinyPNG**: https://tinypng.com/
- **Squoosh**: https://squoosh.app/
- **Live Site**: https://confident-jang-4183f9.netlify.app/
- **Netlify Dashboard**: https://app.netlify.com/

---

## Optional: Check Security Alert

After closing the PRs, check if the critical security alert resolves:
- Visit: https://github.com/NixVir/NixVir.github.io/security/dependabot/80
- It may auto-resolve once obsolete PRs are closed

---

**Note**: Both manual tasks are quick and straightforward. The automated portions (favicon, config, documentation) have all been completed successfully.
