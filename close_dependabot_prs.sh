#!/bin/bash
# Script to close obsolete Dependabot PRs
# These PRs target /themes/gohugo-theme-ananke/src/ which no longer exists

# Note: You may need to authenticate first with: gh auth login

COMMENT="Closing as obsolete - theme updated to newer version (Hugo 0.128.0) which no longer uses npm build dependencies. The /themes/gohugo-theme-ananke/src/ directory targeted by this PR does not exist in the current theme version."

echo "Closing obsolete Dependabot PRs..."
echo "Repository: NixVir/NixVir.github.io"
echo ""

# PR #17 - decode-uri-component
echo "Closing PR #17 (decode-uri-component 0.2.0 → 0.2.2)..."
gh pr close 17 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #16 - loader-utils and webpack
echo "Closing PR #16 (loader-utils + webpack)..."
gh pr close 16 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #14 - async
echo "Closing PR #14 (async 2.6.1 → 2.6.4)..."
gh pr close 14 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #13 - path-parse
echo "Closing PR #13 (path-parse 1.0.5 → 1.0.7)..."
gh pr close 13 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #12 - hosted-git-info
echo "Closing PR #12 (hosted-git-info 2.7.1 → 2.8.9)..."
gh pr close 12 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #11 - lodash
echo "Closing PR #11 (lodash 4.17.15 → 4.17.21)..."
gh pr close 11 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #10 - y18n
echo "Closing PR #10 (y18n 3.2.1 → 3.2.2)..."
gh pr close 10 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #9 - elliptic
echo "Closing PR #9 (elliptic 6.4.1 → 6.5.4)..."
gh pr close 9 --repo NixVir/NixVir.github.io --comment "$COMMENT"

# PR #6 - jquery
echo "Closing PR #6 (jquery 3.4.0 → 3.5.0)..."
gh pr close 6 --repo NixVir/NixVir.github.io --comment "$COMMENT"

echo ""
echo "✓ All 9 obsolete Dependabot PRs closed!"
echo ""
echo "Note: If you see authentication errors, run: gh auth login"
