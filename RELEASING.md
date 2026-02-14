# Release Guide

Quick reference for creating releases and publishing containers.

## Creating a Release

### 1. Prepare the Release

Ensure main branch is ready:
```bash
git checkout main
git pull origin main
```

Update version numbers if needed:
- `README.md` - Update version in example output
- Any other version references

### 2. Create Git Tag

```bash
# Create an annotated tag with release notes
git tag -a v1.0.0 -m "Release v1.0.0

New Features:
- Feature 1 description
- Feature 2 description

Bug Fixes:
- Fix for issue #123
- Fix for issue #456

Breaking Changes:
- None

73! 📡"
```

### 3. Push the Tag

```bash
# Push the tag to GitHub
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build multi-platform Docker images (amd64, arm64, armv7)
2. Push to `ghcr.io/ben-kuhn/packetqth` with tags:
   - `1.0.0` (exact version)
   - `1.0` (major.minor)
   - `1` (major)
   - `latest` (if on main branch)
3. Generate build provenance attestation

### 4. Monitor the Build

Watch the build progress:
```bash
# Open in browser
open https://github.com/ben-kuhn/packetqth/actions
```

Or use GitHub CLI:
```bash
gh run watch
```

### 5. Create GitHub Release

After the build succeeds, create a GitHub release:

**Option A: GitHub Web UI**
1. Go to https://github.com/ben-kuhn/packetqth/releases
2. Click "Draft a new release"
3. Select the tag you just created
4. Title: "PacketQTH v1.0.0"
5. Description: Copy from git tag message
6. Publish release

**Option B: GitHub CLI**
```bash
gh release create v1.0.0 \
  --title "PacketQTH v1.0.0" \
  --notes "See CHANGELOG.md for details"
```

### 6. Verify the Release

Test the published image:
```bash
# Pull the new version
docker pull ghcr.io/ben-kuhn/packetqth:1.0.0

# Test it
docker run --rm ghcr.io/ben-kuhn/packetqth:1.0.0 --help
```

### 7. Announce the Release

Optional: Announce on:
- GitHub Discussions
- Project website
- Amateur radio forums
- Social media

## Versioning Strategy

PacketQTH uses [Semantic Versioning](https://semver.org/):

**Format:** `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Examples:**
- `v1.0.0` - First stable release
- `v1.1.0` - New feature added
- `v1.1.1` - Bug fix
- `v2.0.0` - Breaking change

## Pre-Releases

For testing before official release:

```bash
# Create a pre-release tag
git tag -a v1.1.0-rc1 -m "Release candidate 1 for v1.1.0"
git push origin v1.1.0-rc1
```

This will build and publish as:
- `ghcr.io/ben-kuhn/packetqth:1.1.0-rc1`

Mark as pre-release in GitHub Releases.

## Hotfix Releases

For urgent bug fixes:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/1.0.1 v1.0.0

# Make fixes
# ... edit files ...
git commit -am "Fix critical bug"

# Merge back to main
git checkout main
git merge hotfix/1.0.1

# Tag the hotfix
git tag -a v1.0.1 -m "Hotfix v1.0.1: Fix critical bug"
git push origin main v1.0.1

# Delete hotfix branch
git branch -d hotfix/1.0.1
```

## Rollback

If a release has issues:

### Option 1: New Patch Release

Recommended - fix forward:
```bash
# Fix the issue
git commit -am "Fix issue from v1.0.0"

# Release new version
git tag -a v1.0.1 -m "Fix for v1.0.0"
git push origin v1.0.1
```

### Option 2: Delete Tag (Use with Caution)

Only if release was just created:
```bash
# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin :refs/tags/v1.0.0

# Note: This doesn't remove published containers
# Users may have already pulled the image
```

## Container Image Management

### Making Images Public

After first push, make the package public:

1. Go to https://github.com/ben-kuhn?tab=packages
2. Click on `packetqth` package
3. Settings → Change visibility → Public
4. Confirm

### Deleting Old Images

Clean up old development images periodically:

1. Go to package settings
2. Select old versions (e.g., `main-abc123` commits)
3. Delete unneeded versions
4. Keep: all version tags, latest, main

## Testing Checklist

Before creating a release, ensure:

- [ ] All tests pass locally
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Version numbers are bumped (if applicable)
- [ ] Docker image builds locally
- [ ] No secrets in code
- [ ] README examples work
- [ ] TOTP setup tools work
- [ ] All dependencies are pinned

## Automation

The release process is automated through GitHub Actions:

**What's automated:**
- ✅ Multi-platform Docker builds
- ✅ Publishing to ghcr.io
- ✅ Version tag extraction
- ✅ Build attestation generation
- ✅ Layer caching for faster builds

**What's manual:**
- Creating git tags
- Writing release notes
- Creating GitHub releases
- Making packages public
- Announcements

## Release Schedule

Suggested release cadence:

- **Patch releases**: As needed for bug fixes
- **Minor releases**: Monthly or when features are ready
- **Major releases**: Yearly or for breaking changes

## Emergency Releases

For critical security issues:

1. Create hotfix immediately
2. Tag and release ASAP
3. Mark as critical in release notes
4. Announce on all channels
5. Update security documentation

## Example Release Workflow

Complete example:

```bash
# 1. Update code
git checkout main
git pull

# 2. Update docs
vim CHANGELOG.md
git commit -am "Update changelog for v1.0.0"

# 3. Tag release
git tag -a v1.0.0 -m "Release v1.0.0

Features:
- Initial stable release

73!"

# 4. Push
git push origin main
git push origin v1.0.0

# 5. Wait for build (check GitHub Actions)
gh run watch

# 6. Test
docker pull ghcr.io/ben-kuhn/packetqth:1.0.0
docker run --rm ghcr.io/ben-kuhn/packetqth:1.0.0 --help

# 7. Create GitHub release
gh release create v1.0.0 \
  --title "PacketQTH v1.0.0" \
  --notes-file CHANGELOG.md

# 8. Make package public (first time only)
# Visit https://github.com/ben-kuhn?tab=packages

# Done! 🎉
```

---

**73!** 🏷️📦
