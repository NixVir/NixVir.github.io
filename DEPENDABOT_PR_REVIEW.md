# Dependabot PR Review and Recommendations

**Date**: October 20, 2025
**Repository**: NixVir/NixVir.github.io

## Summary

There are **9 open Dependabot pull requests** from 2020-2022. After investigation, these PRs target a directory (`/themes/gohugo-theme-ananke/src/`) that **no longer exists** in the current version of the theme.

## Status of Open PRs

All 9 PRs attempt to update npm dependencies in the theme's build system:

| PR # | Package | From | To | Created | Status |
|------|---------|------|-----|---------|--------|
| 17 | decode-uri-component | 0.2.0 | 0.2.2 | Dec 2022 | Obsolete |
| 16 | loader-utils + webpack | 1.1.0/2.7.0 | 1.4.2/5.75.0 | Nov 2022 | Obsolete |
| 14 | async | 2.6.1 | 2.6.4 | Apr 2022 | Obsolete |
| 13 | path-parse | 1.0.5 | 1.0.7 | Aug 2021 | Obsolete |
| 12 | hosted-git-info | 2.7.1 | 2.8.9 | May 2021 | Obsolete |
| 11 | lodash | 4.17.15 | 4.17.21 | May 2021 | Obsolete |
| 10 | y18n | 3.2.1 | 3.2.2 | Mar 2021 | Obsolete |
| 9 | elliptic | 6.4.1 | 6.5.4 | Mar 2021 | Obsolete |
| 6 | jquery | 3.4.0 | 3.5.0 | Apr 2020 | Obsolete |

## Why These PRs Are Obsolete

1. **Theme Updated**: The site was upgraded to the latest Ananke theme on September 12, 2025
2. **No src/ Directory**: The current theme version doesn't have a `src/` directory with build dependencies
3. **Modern Hugo**: Hugo 0.128.0 uses Hugo Modules/Pipes instead of npm build system
4. **Pre-compiled Theme**: You're using the pre-built theme, not building from source

## Current Theme Structure

```
themes/gohugo-theme-ananke/
├── archetypes/
├── assets/          # Hugo assets (not npm)
├── config/
├── i18n/
├── images/
├── layouts/
├── go.mod          # Hugo module system
└── package.hugo.json
```

No `package.json`, `node_modules/`, or `src/` directory exists.

## Recommendations

### Immediate Actions

1. **Close All 9 PRs** - These target files that don't exist
   - Can be closed via GitHub web interface
   - Add comment: "Closing as obsolete - theme updated to newer version without npm dependencies"

2. **Disable Dependabot for Theme** - Prevent future obsolete PRs
   - Create/update `.github/dependabot.yml`
   - Ignore the `themes/` directory

3. **Review Security Alert #80** - One critical vulnerability was mentioned
   - Visit: https://github.com/NixVir/NixVir.github.io/security/dependabot/80
   - May be auto-resolved by theme update

### Long-term Considerations

1. **Pin Theme Version** - Use Hugo modules with specific version
2. **Enable Dependabot for Main Site** - If you add any npm dependencies to your main site
3. **Regular Theme Updates** - Check for Ananke updates quarterly

## How to Close the PRs

### Option 1: Via GitHub CLI (gh)

```bash
gh pr close 17 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 16 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 14 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 13 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 12 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 11 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 10 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 9 -c "Obsolete - theme updated, src/ directory no longer exists"
gh pr close 6 -c "Obsolete - theme updated, src/ directory no longer exists"
```

### Option 2: Via GitHub Web Interface

1. Go to https://github.com/NixVir/NixVir.github.io/pulls
2. Click on each PR
3. Click "Close pull request"
4. Add comment explaining obsolescence

## Dependabot Configuration (Optional)

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Disable for themes directory
  - package-ecosystem: "npm"
    directory: "/themes/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 0
```

## Security Note

The theme update to the latest version (September 2025) likely resolved any security vulnerabilities that existed in the old npm dependencies. The current theme uses Hugo's built-in asset pipeline instead of webpack/npm.

---

**Action Items**:
- [ ] Close 9 obsolete Dependabot PRs
- [ ] Check security alert #80 status
- [ ] Consider adding dependabot.yml to prevent future theme PRs
