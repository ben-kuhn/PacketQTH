#!/usr/bin/env python3
"""
PacketQTH Setup Wizard

Interactive TUI wizard for initial configuration. Produces:
  .env              - HA token and secrets
  config.yaml       - Full application config
  users.yaml        - Initial user TOTP setup
  docker-compose.generated.yml - Ready-to-use compose file
"""

import argparse
import asyncio
import copy
import os
import re
import sys
import subprocess
import aiohttp
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
    """Write dict to .env file with owner-only permissions (0o600).

    Callers must pass the full env dict (loaded via load_env) with their
    changes merged in — this function replaces the entire file.
    """
    content = "".join(f"{k}={v}\n" for k, v in values.items())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)
    # Ensure permissions are correct even if file already existed.
    # May fail on container bind-mounts (rootless Podman restriction) — not fatal.
    try:
        os.chmod(path, 0o600)
    except PermissionError:
        pass


def load_config(path: Path) -> dict[str, Any]:
    """Load config.yaml. Returns DEFAULT_CONFIG structure if file missing."""
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
    """Write users dict to users.yaml under 'users' key with owner-only permissions (0o600)."""
    content = yaml.dump({"users": users}, default_flow_style=False)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)
    # Ensure permissions are correct even if file already existed.
    # May fail on container bind-mounts (rootless Podman restriction) — not fatal.
    try:
        os.chmod(path, 0o600)
    except PermissionError:
        pass


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place (recursive for nested dicts)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Step 1: HomeAssistant Connection
# ---------------------------------------------------------------------------

def _ha_headers(token: str) -> dict[str, str]:
    """Return Authorization headers for HA API requests."""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def test_ha_connection(url: str, token: str) -> tuple[int | None, str | None]:
    """
    Test HA connection by fetching /api/states.
    Returns (entity_count, None) on success or (None, error_message) on failure.
    """
    headers = _ha_headers(token)
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            resp = await session.get(f"{url.rstrip('/')}/api/states", headers=headers)
            if resp.status == 401:
                return None, "Unauthorized (401) — check your token"
            if resp.status != 200:
                return None, f"Unexpected status {resp.status}"
            states = await resp.json()
            return len(states), None
    except aiohttp.ClientConnectorError as e:
        return None, f"Connection failed: {e}"
    except Exception as e:
        return None, f"Error: {e}"


def step_ha_connection(config: dict, env: dict, config_path: Path, env_path: Path) -> tuple[str, str]:
    """
    Prompt for HA URL and token. Test connection. Write .env and config.yaml.
    Returns (url, token) for use in later steps.
    """
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML

    print("\n" + "=" * 60)
    print("Step 1/5: HomeAssistant Connection")
    print("=" * 60)

    current_url = config.get("homeassistant", {}).get("url", DEFAULT_CONFIG["homeassistant"]["url"])
    current_token = env.get("HA_TOKEN", "")

    while True:
        url = prompt(
            HTML(f"HomeAssistant URL [<ansigreen>{current_url}</ansigreen>]: "),
        ).strip() or current_url

        token_hint = f"***{current_token[-6:]}" if len(current_token) > 6 else ("(set)" if current_token else "(not set)")
        token = prompt(
            HTML(f"HA Long-Lived Access Token [<ansigreen>{token_hint}</ansigreen>]: "),
            is_password=True,
        ).strip() or current_token

        print("\nTesting connection...", end=" ", flush=True)
        count, err = asyncio.run(test_ha_connection(url, token))
        if not err:
            print(f"Connected ({count} entities found)")
            break
        print(f"FAILED\n  {err}")
        if prompt("Retry? [y/N]: ").strip().lower() != "y":
            print("Skipping connection test — continuing with provided values.")
            break
        current_url = url
        current_token = token

    env["HA_TOKEN"] = token
    save_env(env, env_path)
    config.setdefault("homeassistant", {})
    config["homeassistant"]["url"] = url
    config["homeassistant"]["token"] = "${HA_TOKEN}"
    save_config(config, config_path)
    print(f"  Wrote {env_path}")
    print(f"  Wrote {config_path}")
    return url, token


# ---------------------------------------------------------------------------
# Step 2: Server Config
# ---------------------------------------------------------------------------

def parse_server_inputs(port: str, timeout: str, max_attempts: str) -> dict:
    """Parse and validate server config inputs. Uses defaults for empty strings."""
    def _int(val: str, default: int, name: str) -> int:
        if not val.strip():
            return default
        try:
            return int(val.strip())
        except ValueError:
            raise ValueError(f"Invalid {name}: {val!r} — must be an integer")

    port_val = _int(port, 8023, "port")
    if not (1 <= port_val <= 65535):
        raise ValueError(f"Invalid port: {port_val} — must be 1–65535")
    return {
        "port": port_val,
        "timeout_seconds": _int(timeout, 300, "timeout"),
        "max_auth_attempts": _int(max_attempts, 3, "max_attempts"),
    }


def step_server_config(config: dict, config_path: Path) -> None:
    """Prompt for server settings and write to config.yaml."""
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML

    print("\n" + "=" * 60)
    print("Step 2/5: Server Settings")
    print("=" * 60)

    telnet = config.get("telnet", {})
    security = config.get("security", {})

    cur_port = telnet.get("port", 8023)
    cur_timeout = telnet.get("timeout_seconds", 300)
    cur_attempts = security.get("max_auth_attempts", 3)

    while True:
        try:
            inputs = parse_server_inputs(
                port=prompt(HTML(f"Telnet port [<ansigreen>{cur_port}</ansigreen>]: ")).strip(),
                timeout=prompt(HTML(f"Session timeout in seconds [<ansigreen>{cur_timeout}</ansigreen>]: ")).strip(),
                max_attempts=prompt(HTML(f"Max failed auth attempts [<ansigreen>{cur_attempts}</ansigreen>]: ")).strip(),
            )
            break
        except ValueError as e:
            print(f"  Error: {e} — please try again")

    config.setdefault("telnet", {}).update({
        "port": inputs["port"],
        "timeout_seconds": inputs["timeout_seconds"],
    })
    config.setdefault("security", {})["max_auth_attempts"] = inputs["max_auth_attempts"]
    save_config(config, config_path)
    print(f"  Wrote {config_path}")


# ---------------------------------------------------------------------------
# Step 3: Entity Filter
# ---------------------------------------------------------------------------

async def fetch_all_entities(url: str, token: str) -> list[dict]:
    """Fetch all entity states from HA API."""
    headers = _ha_headers(token)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        resp = await session.get(f"{url.rstrip('/')}/api/states", headers=headers)
        resp.raise_for_status()
        return await resp.json()


def group_entities_by_domain(entities: list[dict]) -> dict[str, list[str]]:
    """Group entity_ids by domain, sorted within each domain."""
    grouped: dict[str, list[str]] = {}
    for entity in entities:
        eid = entity.get("entity_id", "")
        if "." not in eid:
            continue
        domain = eid.split(".")[0]
        grouped.setdefault(domain, []).append(eid)
    for domain in grouped:
        grouped[domain].sort()
    return grouped


def build_entity_filter(
    all_entities: list[dict],
    selected_domains: list[str],
    selected_entities: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """
    Build include_domains and exclude_entities lists from selections.
    Entities within selected domains that were NOT chosen become exclude_entities.
    """
    grouped = group_entities_by_domain(all_entities)
    exclude_entities = []
    for domain in selected_domains:
        domain_entities = grouped.get(domain, [])
        chosen = set(selected_entities.get(domain, []))
        for eid in domain_entities:
            if eid not in chosen:
                exclude_entities.append(eid)
    return sorted(selected_domains), sorted(exclude_entities)


def step_entity_filter(config: dict, config_path: Path, ha_url: str, ha_token: str) -> None:
    """
    Interactively build entity filter. Skippable if HA unreachable.
    Writes entity_filter section to config.yaml.
    """
    from prompt_toolkit import prompt
    from prompt_toolkit.shortcuts import checkboxlist_dialog
    from prompt_toolkit.styles import Style

    print("\n" + "=" * 60)
    print("Step 3/5: Entity Filter")
    print("  (Enter 'n' to skip if HomeAssistant is unavailable)")
    print("=" * 60)

    skip = prompt("Fetch entities from HomeAssistant now? [Y/n]: ").strip().lower()
    if skip == "n":
        print("  Skipped — keeping existing entity_filter config.")
        return

    # Fetch entities
    print("Fetching entities...", end=" ", flush=True)
    try:
        entities = asyncio.run(fetch_all_entities(ha_url, ha_token))
        print(f"{len(entities)} entities found")
    except Exception as e:
        print(f"FAILED: {e}")
        print("  Skipping entity filter step.")
        return

    grouped = group_entities_by_domain(entities)
    all_domains = sorted(grouped.keys())

    # Current selections from config
    ef = config.get("homeassistant", {}).get("entity_filter", {})
    current_inc_domains = set(ef.get("include_domains") or [])
    current_exc_entities = set(ef.get("exclude_entities") or [])

    # Domain selection dialog
    style = Style.from_dict({"dialog": "bg:#1e1e2e", "dialog.body": "bg:#1e1e2e fg:#cdd6f4"})
    domain_choices = [(d, f"{d}  ({len(grouped[d])} entities)") for d in all_domains]
    default_domains = [d for d in all_domains if d in current_inc_domains] or \
                      [d for d in all_domains if d in {"light", "switch", "automation", "cover", "sensor", "climate", "fan", "lock"}]

    selected_domains = checkboxlist_dialog(
        title="Select domains to include",
        text="Space to toggle, Enter to confirm:",
        values=domain_choices,
        default_values=default_domains,
        style=style,
    ).run()

    if selected_domains is None:
        print("  Cancelled — keeping existing entity_filter config.")
        return

    # Per-domain entity selection
    selected_entities: dict[str, list[str]] = {}
    for domain in selected_domains:
        domain_eids = grouped[domain]
        entity_choices = [(eid, eid) for eid in domain_eids]
        default_eids = [eid for eid in domain_eids if eid not in current_exc_entities]

        chosen = checkboxlist_dialog(
            title=f"Select entities to include — {domain} ({len(domain_eids)} total)",
            text="Space to toggle, Enter to confirm:",
            values=entity_choices,
            default_values=default_eids,
            style=style,
        ).run()

        if chosen is None:
            print(f"  Cancelled on domain '{domain}' — keeping existing config.")
            return
        if not chosen:
            print(f"  Warning: no entities selected for '{domain}' — all {len(domain_eids)} will be excluded.")
            confirm = prompt("Continue anyway? [y/N]: ").strip().lower()
            if confirm != "y":
                print("  Cancelled — keeping existing entity_filter config.")
                return
        selected_entities[domain] = chosen

    inc_domains, exc_entities = build_entity_filter(entities, selected_domains, selected_entities)

    config.setdefault("homeassistant", {}).setdefault("entity_filter", {}).update({
        "include_domains": inc_domains,
        "exclude_domains": None,
        "include_entities": None,
        "exclude_entities": exc_entities,
    })
    save_config(config, config_path)
    print(f"  {len(inc_domains)} domains, {len(exc_entities)} excluded entities")
    print(f"  Wrote {config_path}")


# ---------------------------------------------------------------------------
# Step 4: Initial User Setup
# ---------------------------------------------------------------------------

def parse_totp_secret_from_output(callsign: str, output: str) -> str | None:
    """
    Extract TOTP secret from setup_totp.py output.
    Looks for line: '  CALLSIGN: "SECRET"'
    """
    pattern = rf'^\s+{re.escape(callsign.upper())}:\s+"([A-Z2-7]+)"'
    for line in output.splitlines():
        m = re.match(pattern, line)
        if m:
            return m.group(1)
    return None


def step_user_setup(users_path: Path) -> None:
    """
    Prompt for callsign, run setup_totp.py, write users.yaml.
    Skippable if users.yaml already has entries.
    """
    from prompt_toolkit import prompt

    print("\n" + "=" * 60)
    print("Step 4/5: Initial User Setup")
    print("=" * 60)

    existing_users = load_users(users_path)
    if existing_users:
        user_list = ", ".join(existing_users.keys())
        skip = prompt(f"users.yaml already has users ({user_list}). Add another? [y/N]: ").strip().lower()
        if skip != "y":
            print("  Skipped.")
            return

    callsign = prompt("Callsign: ").strip().upper()
    if not callsign:
        print("  No callsign entered — skipping.")
        return

    # Run setup_totp.py, forwarding output to terminal while capturing it
    script = Path(__file__).parent / "setup_totp.py"
    print()
    collected_lines = []
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), callsign],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            print(line, end="", flush=True)
            collected_lines.append(line)
        proc.wait()
        if proc.returncode != 0:
            print(f"\n  Warning: setup_totp.py exited with code {proc.returncode}")
    except FileNotFoundError:
        print(f"  Error: could not find {script}")
        return

    output = "".join(collected_lines)
    secret = parse_totp_secret_from_output(callsign, output)
    if not secret:
        print("\n  Warning: could not extract secret from output — users.yaml not updated.")
        print(f"  Add it manually: {callsign}: \"<SECRET>\"")
        return

    existing_users[callsign] = secret
    save_users(existing_users, users_path)
    print(f"\n  Wrote {users_path}")


# ---------------------------------------------------------------------------
# Step 5: Docker Compose
# ---------------------------------------------------------------------------

def generate_compose(host_port: int, config_dir: str, uid: int, gid: int) -> str:
    """Generate docker-compose YAML string from parameters."""
    compose = {
        "services": {
            "packetqth": {
                "image": "ghcr.io/ben-kuhn/packetqth:latest",
                "container_name": "packetqth",
                "restart": "unless-stopped",
                "user": f"{uid}:{gid}",
                "ports": [f"127.0.0.1:{host_port}:8023"],
                "volumes": [
                    f"{config_dir}/config.yaml:/app/config.yaml:ro",
                    f"{config_dir}/users.yaml:/app/users.yaml:ro",
                    f"{config_dir}/logs:/app/logs",
                ],
                "environment": [
                    "HA_TOKEN=${HA_TOKEN}",
                    "LOG_LEVEL=${LOG_LEVEL:-INFO}",
                ],
                "networks": ["homeassistant"],
                "security_opt": ["no-new-privileges:true"],
                "cap_drop": ["ALL"],
                "read_only": True,
                "tmpfs": ["/tmp"],
                "deploy": {
                    "resources": {
                        "limits": {"cpus": "0.5", "memory": "256M"},
                        "reservations": {"cpus": "0.1", "memory": "64M"},
                    }
                },
            }
        },
        "networks": {
            "homeassistant": {"external": False, "driver": "bridge"}
        },
    }
    return yaml.dump(compose, default_flow_style=False, sort_keys=False)


def step_docker_compose(output_path: Path) -> None:
    """Prompt for host port and config dir, write docker-compose.generated.yml."""
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML

    print("\n" + "=" * 60)
    print("Step 5/5: Docker Compose")
    print("=" * 60)

    default_port = 8023
    # Default to the directory containing the output file (same as config files).
    # When running in a container this is the container-side mount path (e.g. /config);
    # the user should replace it with the equivalent host path.
    default_dir = str(output_path.parent)

    while True:
        port_str = prompt(HTML(f"Host port to expose telnet on [<ansigreen>{default_port}</ansigreen>]: ")).strip()
        if not port_str:
            host_port = default_port
            break
        if port_str.isdigit() and 1 <= int(port_str) <= 65535:
            host_port = int(port_str)
            break
        print(f"  Invalid port {port_str!r} — must be 1–65535")

    print("  Enter the absolute path on the HOST machine where your config files")
    print("  will live (the directory you mounted with -v ...:/config).")
    config_dir_input = prompt(HTML(f"Host config directory [<ansigreen>{default_dir}</ansigreen>]: ")).strip() or default_dir
    config_dir = str(Path(config_dir_input).resolve())

    # Create logs directory next to config files so the container can write to it
    logs_dir = Path(config_dir) / "logs"
    logs_dir.mkdir(exist_ok=True)

    compose_yaml = generate_compose(
        host_port=host_port,
        config_dir=config_dir,
        uid=os.getuid(),
        gid=os.getgid(),
    )
    output_path.write_text(compose_yaml)

    print(f"\n  Written to: {output_path}")
    print(f"  Logs directory: {logs_dir}")
    print("\n  To use it, run:")
    print(f"    mv {output_path.name} docker-compose.yml")
    print("    docker compose up -d")


# ---------------------------------------------------------------------------
# Main Wizard
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="PacketQTH Setup Wizard")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    parser.add_argument("--users", default="users.yaml", help="Path to users.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    env_path = Path(args.env)
    users_path = Path(args.users)
    compose_path = config_path.parent / "docker-compose.generated.yml"

    print("=" * 60)
    print("  PacketQTH Setup Wizard")
    print("=" * 60)
    if config_path.exists():
        print(f"  Existing config found at {config_path} — pre-filling values.")
    else:
        print("  No existing config found — starting fresh.")

    # Load existing state
    config = load_config(config_path)
    env = load_env(env_path)

    # Run steps
    ha_url, ha_token = step_ha_connection(config, env, config_path, env_path)
    step_server_config(config, config_path)
    step_entity_filter(config, config_path, ha_url, ha_token)
    step_user_setup(users_path)
    step_docker_compose(compose_path)

    print("\n" + "=" * 60)
    print("  Setup complete!")
    print(f"  Config:  {config_path}")
    print(f"  Env:     {env_path}")
    print(f"  Users:   {users_path}")
    print(f"  Compose: {compose_path}")
    print("=" * 60)
    print("\n73!")


if __name__ == "__main__":
    main()
