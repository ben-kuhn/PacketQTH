# GitHub Actions Workflows

## Docker Build and Publish

The `docker-publish.yml` workflow automatically builds and publishes two Docker containers to GitHub Container Registry (ghcr.io):

1. **Runtime image** (`packetqth`) - Minimal dependencies for running the server
2. **Tools image** (`packetqth-tools`) - Includes QR code support for TOTP setup

### Triggers

**Automatic builds on:**
- Push to `main` branch → publishes `latest` and `main-<sha>` tags
- Push version tag (e.g., `v1.0.0`) → publishes versioned tags
- Pull requests → builds but does not publish (test only)

### Tags Generated

**Runtime Image:**

For version tags (e.g., `v1.0.0`):
- `ghcr.io/ben-kuhn/packetqth:1.0.0`
- `ghcr.io/ben-kuhn/packetqth:1.0`
- `ghcr.io/ben-kuhn/packetqth:1`
- `ghcr.io/ben-kuhn/packetqth:latest`

For main branch pushes:
- `ghcr.io/ben-kuhn/packetqth:main`
- `ghcr.io/ben-kuhn/packetqth:main-<git-sha>`
- `ghcr.io/ben-kuhn/packetqth:latest`

**Tools Image:**

Same pattern with `-tools` suffix:
- `ghcr.io/ben-kuhn/packetqth-tools:1.0.0`
- `ghcr.io/ben-kuhn/packetqth-tools:latest`
- etc.

**For pull requests:**
- Both images built but not pushed to registry

### Platform Support

Multi-platform images built for:
- `linux/amd64` - Standard x86_64 servers
- `linux/arm64` - ARM64 systems (Raspberry Pi 4, Apple Silicon)
- `linux/arm/v7` - ARM v7 systems (Raspberry Pi 3)

### Creating a Release

To publish a new versioned release:

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0: Description"

# Push the tag
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build multi-platform Docker images
2. Push to ghcr.io with version tags
3. Update the `latest` tag
4. Generate build attestation

### Using Published Images

**Runtime image (running the server):**
```bash
# Pull the latest version
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Run with docker-compose
docker-compose up -d
```

**Tools image (TOTP setup with QR codes):**
```bash
# Generate TOTP secret with QR code
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN

# Save QR code to file
docker run --rm -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png
```

### Permissions

The workflow uses the `GITHUB_TOKEN` automatically provided by GitHub Actions. No manual configuration required.

**Required permissions:**
- `contents: read` - Read repository content
- `packages: write` - Push to GitHub Container Registry
- `id-token: write` - Generate build attestation

### Build Cache

The workflow uses GitHub Actions cache to speed up builds:
- Cache is shared between builds
- Reduces build time significantly
- Automatically managed by GitHub

### Security

**Build attestations:**
- Each published image has cryptographic attestation
- Proves the image was built by this repository
- Verifies supply chain integrity

**Container scanning:**
- Consider adding `trivy-action` for vulnerability scanning
- Example in comments below

### Troubleshooting

**Build failures:**
1. Check the Actions tab in GitHub
2. Review build logs for errors
3. Test locally: `docker build .`

**Permission denied:**
- Ensure repository has Packages enabled
- Check workflow permissions in Settings → Actions

**Image not public:**
- By default, images are private
- Make public: ghcr.io → Package → Settings → Change visibility

### Future Enhancements

Optional additions:
```yaml
# Add vulnerability scanning
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}
    format: 'sarif'
    output: 'trivy-results.sarif'

# Add image signing with cosign
- name: Install cosign
  uses: sigstore/cosign-installer@main
- name: Sign container image
  run: cosign sign --yes ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build-and-push.outputs.digest }}
```
