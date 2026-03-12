# PacketQTH Setup Wizard — Design Document

**Date:** 2026-03-12
**Status:** Approved

## Overview

A self-contained TUI setup wizard (`tools/configure.py`) that walks a new user through all configuration needed to run PacketQTH. It detects existing config and pre-fills values, making it safe to re-run for updates.

## Artifacts Produced

| File | Description |
|------|-------------|
| `.env` | HA token and URL for Docker secrets |
| `config.yaml` | Full app config (HA connection, server settings, entity filter) |
| `users.yaml` | Initial user callsign + TOTP secret |
| `docker-compose.generated.yml` | Ready-to-use compose file (does not overwrite existing) |

## Steps

### Step 1/5 — HomeAssistant Connection
- Prompt for HA URL (default: `http://homeassistant.local:8123`)
- Prompt for HA Long-Lived Access Token (masked input, shows last 6 chars if existing)
- Test connection via `aiohttp`; show entity count on success
- On failure: offer retry or skip
- Writes HA URL and token to `.env`; writes `homeassistant` section to `config.yaml`

### Step 2/5 — Server Settings
- Prompt for telnet port (default: `8023`)
- Prompt for session timeout in seconds (default: `300`)
- Prompt for max failed auth attempts (default: `5`)
- Writes `server` section to `config.yaml`

### Step 3/5 — Entity Filter (skippable)
- Requires live HA connection from Step 1; skippable if unavailable
- **Screen A — Domain selection:** `prompt_toolkit` checkbox list showing each domain with entity count; pre-selects previously configured domains
- **Screen B — Entity selection:** per-domain `prompt_toolkit` checkbox list with fuzzy search; pre-selects previously included entities
- Generates `include_domains` list and `exclude_entities` list (entities within selected domains that were NOT chosen)
- Writes `entity_filter` section to `config.yaml`

### Step 4/5 — Initial User Setup
- Prompt for callsign
- Invokes `tools/setup_totp.py <callsign>` as subprocess
- QR code and TOTP secret output flows through to terminal
- Skippable if `users.yaml` already contains at least one user

### Step 5/5 — Docker Compose
- Prompt for host port (default: `8023`)
- Prompt for config directory path (default: current working directory)
- Writes `docker-compose.generated.yml` (never overwrites `docker-compose.yml`)
- Prints rename instructions:
  ```
  mv docker-compose.generated.yml docker-compose.yml
  docker compose up -d
  ```

## Technology

- **Script:** `tools/configure.py` — single self-contained file
- **TUI library:** `prompt_toolkit` — added to `requirements-tools.txt`
- **HA fetch:** direct `aiohttp` calls (does not import app internals)
- **Config read/write:** `PyYAML` with round-trip preservation of comments where possible
- **TOTP:** delegates to `tools/setup_totp.py` subprocess

## Resumability

On startup, the wizard checks for existing `config.yaml` and `.env` and pre-fills all prompts with current values. Each step writes its outputs immediately so a partial run leaves valid partial config.

## Dependencies Added

`requirements-tools.txt`:
```
prompt_toolkit>=3.0.0
```

All other needed packages (`aiohttp`, `PyYAML`, `pyotp`) are already in `requirements.txt`.

## Docker Usage

```bash
docker run --rm -it \
  -v $(pwd):/config \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/configure.py
```
