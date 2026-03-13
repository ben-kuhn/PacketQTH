#!/usr/bin/env python3
"""
PacketQTH Setup Wizard

Interactive TUI wizard for initial configuration. Produces:
  .env              - HA token and secrets
  config.yaml       - Full application config
  users.yaml        - Initial user TOTP setup
  docker-compose.generated.yml - Ready-to-use compose file
"""

import os
import sys
import asyncio
import subprocess
import yaml
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "telnet": {
        "host": "0.0.0.0",
        "port": 8023,
        "max_connections": 10,
        "timeout_seconds": 300,
        "bpq_mode": True,
    },
    "homeassistant": {
        "url": "http://homeassistant.local:8123",
        "token": "${HA_TOKEN}",
        "cache_ttl": 60,
        "entity_filter": {
            "include_domains": ["light", "switch", "automation", "cover", "sensor", "climate", "fan", "lock"],
            "exclude_domains": None,
            "include_entities": None,
            "exclude_entities": [],
        },
    },
    "auth": {"users_file": "users.yaml"},
    "display": {"page_size": 10},
    "security": {
        "welcome_banner": "PacketQTH v0.1.0",
        "max_auth_attempts": 3,
        "ip_safelist": [],
    },
}

# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict[str, str]:
    """Load .env file into dict. Returns empty dict if file missing."""
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def save_env(values: dict[str, str], path: Path) -> None:
    """Write dict to .env file."""
    lines = [f"{k}={v}\n" for k, v in values.items()]
    path.write_text("".join(lines))


def load_config(path: Path) -> dict[str, Any]:
    """Load config.yaml. Returns DEFAULT_CONFIG structure if file missing."""
    import copy
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    if not path.exists():
        return defaults
    loaded = yaml.safe_load(path.read_text()) or {}
    # Deep merge loaded values over defaults
    _deep_merge(defaults, loaded)
    return defaults


def save_config(config: dict[str, Any], path: Path) -> None:
    """Write config dict to YAML file."""
    path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def load_users(path: Path) -> dict[str, str]:
    """Load users.yaml. Returns empty dict if missing."""
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text()) or {}
    return loaded.get("users", {})


def save_users(users: dict[str, str], path: Path) -> None:
    """Write users dict to users.yaml under 'users' key."""
    path.write_text(yaml.dump({"users": users}, default_flow_style=False))


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place (recursive for nested dicts)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


if __name__ == "__main__":
    print("PacketQTH Setup Wizard — run with: python tools/configure.py")
