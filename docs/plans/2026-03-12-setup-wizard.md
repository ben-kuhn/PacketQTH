# Setup Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `tools/configure.py`, a self-contained 5-step TUI setup wizard that produces `.env`, `config.yaml`, `users.yaml`, and `docker-compose.generated.yml`.

**Architecture:** Single standalone script using `prompt_toolkit` for interactive prompts and `aiohttp` for HA API calls. Does not import app internals. Loads existing config on startup to pre-fill all prompts. Each step writes its output immediately so partial runs leave valid partial config.

**Tech Stack:** Python 3.11, `prompt_toolkit>=3.0.0`, `aiohttp` (existing), `PyYAML` (existing), `pyotp` (existing, for users.yaml format reference only), subprocess for `setup_totp.py`.

---

## Reference: Key Files

- `config.yaml.example` — canonical config structure (all sections, field names, defaults)
- `docker-compose.yml` — template for generated compose file
- `tools/setup_totp.py` — called as subprocess in Step 4; output format: `  CALLSIGN: "SECRET"`
- `requirements-tools.txt` — add `prompt_toolkit>=3.0.0` here
- `Dockerfile.tools` — ensure it still installs `requirements-tools.txt` (no change needed)

## Config/Env Conventions

- HA token: stored in `.env` as `HA_TOKEN=<token>`, referenced in `config.yaml` as `token: ${HA_TOKEN}`
- HA URL: stored directly in `config.yaml` under `homeassistant.url`
- The wizard reads the token in-memory for connection testing; never writes it to `config.yaml`

---

## Task 1: Add prompt_toolkit Dependency

**Files:**
- Modify: `requirements-tools.txt`

**Step 1: Add the dependency**

```
# In requirements-tools.txt, add after qrcode line:
prompt_toolkit>=3.0.0
```

**Step 2: Verify install**

```bash
pip install -r requirements-tools.txt
python -c "from prompt_toolkit import prompt; print('ok')"
```
Expected: `ok`

**Step 3: Commit**

```bash
git add requirements-tools.txt
git commit -m "feat: add prompt_toolkit to tools dependencies"
```

---

## Task 2: Config I/O Helpers

Core functions for reading/writing config files, used by all wizard steps. Write these first with tests before touching any UI code.

**Files:**
- Create: `tools/configure.py` (initial skeleton)
- Create: `tests/tools/test_configure.py`

**Step 1: Write the failing tests**

```python
# tests/tools/test_configure.py
import os
import pytest
import tempfile
import yaml
from pathlib import Path


def test_load_env_returns_empty_dict_when_file_missing(tmp_path):
    from tools.configure import load_env
    result = load_env(tmp_path / ".env")
    assert result == {}


def test_load_env_parses_key_value_pairs(tmp_path):
    from tools.configure import load_env
    env_file = tmp_path / ".env"
    env_file.write_text("HA_TOKEN=abc123\nLOG_LEVEL=INFO\n")
    result = load_env(env_file)
    assert result == {"HA_TOKEN": "abc123", "LOG_LEVEL": "INFO"}


def test_save_env_writes_key_value_pairs(tmp_path):
    from tools.configure import save_env
    env_file = tmp_path / ".env"
    save_env({"HA_TOKEN": "mytoken"}, env_file)
    content = env_file.read_text()
    assert "HA_TOKEN=mytoken" in content


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    from tools.configure import load_config, DEFAULT_CONFIG
    result = load_config(tmp_path / "config.yaml")
    assert result["telnet"]["port"] == DEFAULT_CONFIG["telnet"]["port"]


def test_load_config_reads_existing_file(tmp_path):
    from tools.configure import load_config
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("telnet:\n  port: 9999\n")
    result = load_config(cfg_file)
    assert result["telnet"]["port"] == 9999


def test_save_config_writes_yaml(tmp_path):
    from tools.configure import save_config
    cfg_file = tmp_path / "config.yaml"
    save_config({"telnet": {"port": 8023}}, cfg_file)
    loaded = yaml.safe_load(cfg_file.read_text())
    assert loaded["telnet"]["port"] == 8023


def test_load_users_returns_empty_when_missing(tmp_path):
    from tools.configure import load_users
    result = load_users(tmp_path / "users.yaml")
    assert result == {}


def test_save_users_writes_yaml_with_users_key(tmp_path):
    from tools.configure import save_users
    users_file = tmp_path / "users.yaml"
    save_users({"W1AW": "SECRETBASE32"}, users_file)
    loaded = yaml.safe_load(users_file.read_text())
    assert loaded["users"]["W1AW"] == "SECRETBASE32"
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: `ModuleNotFoundError: No module named 'tools.configure'`

**Step 3: Create `tools/configure.py` with I/O helpers**

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all 9 tests PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add configure.py scaffold with config I/O helpers"
```

---

## Task 3: HA Connection Step (Step 1/5)

Async function to test a HA connection, plus the prompt_toolkit prompts for URL and token.

**Files:**
- Modify: `tools/configure.py`
- Modify: `tests/tools/test_configure.py`

**Step 1: Write failing tests for HA connection logic**

Add to `tests/tools/test_configure.py`:

```python
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_test_ha_connection_returns_count_on_success():
    from tools.configure import test_ha_connection
    mock_states = [{"entity_id": "light.kitchen"}, {"entity_id": "switch.fan"}]
    with patch("aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_states)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "mytoken")
    assert count == 2
    assert err is None


@pytest.mark.asyncio
async def test_test_ha_connection_returns_error_on_auth_failure():
    from tools.configure import test_ha_connection
    with patch("aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "badtoken")
    assert count is None
    assert "401" in err or "Unauthorized" in err.lower()


@pytest.mark.asyncio
async def test_test_ha_connection_returns_error_on_network_failure():
    from tools.configure import test_ha_connection
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientConnectorError(
            MagicMock(), OSError("connection refused")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "token")
    assert count is None
    assert err is not None
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py::test_test_ha_connection_returns_count_on_success -v
```
Expected: `ImportError` or `AttributeError`

**Step 3: Implement `test_ha_connection` and `step_ha_connection` in `tools/configure.py`**

Add after the I/O helpers section:

```python
# ---------------------------------------------------------------------------
# Step 1: HomeAssistant Connection
# ---------------------------------------------------------------------------

async def test_ha_connection(url: str, token: str) -> tuple[int | None, str | None]:
    """
    Test HA connection by fetching /api/states.
    Returns (entity_count, None) on success or (None, error_message) on failure.
    """
    import aiohttp
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url.rstrip('/')}/api/states", headers=headers) as resp:
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

    url = prompt(
        HTML(f"HomeAssistant URL [<ansigreen>{current_url}</ansigreen>]: "),
    ).strip() or current_url

    token_hint = f"***{current_token[-6:]}" if len(current_token) > 6 else ("(set)" if current_token else "(not set)")
    token = prompt(
        HTML(f"HA Long-Lived Access Token [<ansigreen>{token_hint}</ansigreen>]: "),
        is_password=True,
    ).strip() or current_token

    # Test connection
    print("\nTesting connection...", end=" ", flush=True)
    count, err = asyncio.run(test_ha_connection(url, token))
    if err:
        print(f"FAILED\n  {err}")
        retry = prompt("Retry? [y/N]: ").strip().lower()
        if retry == "y":
            return step_ha_connection(config, env, config_path, env_path)
        print("Skipping connection test — continuing with provided values.")
    else:
        print(f"Connected ({count} entities found)")

    # Write outputs
    env["HA_TOKEN"] = token
    save_env(env, env_path)
    config.setdefault("homeassistant", {})["url"] = url
    config["homeassistant"]["token"] = "${HA_TOKEN}"
    save_config(config, config_path)
    print(f"  Wrote {env_path}")
    print(f"  Wrote {config_path}")

    return url, token
```

**Step 4: Run tests**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all tests PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add HA connection step with connection test"
```

---

## Task 4: Server Config Step (Step 2/5)

**Files:**
- Modify: `tools/configure.py`
- Modify: `tests/tools/test_configure.py`

**Step 1: Write failing tests**

Add to `tests/tools/test_configure.py`:

```python
def test_parse_server_inputs_uses_defaults_for_empty():
    from tools.configure import parse_server_inputs
    result = parse_server_inputs(port="", timeout="", max_attempts="")
    assert result["port"] == 8023
    assert result["timeout_seconds"] == 300
    assert result["max_auth_attempts"] == 3


def test_parse_server_inputs_uses_provided_values():
    from tools.configure import parse_server_inputs
    result = parse_server_inputs(port="9000", timeout="600", max_attempts="5")
    assert result["port"] == 9000
    assert result["timeout_seconds"] == 600
    assert result["max_auth_attempts"] == 5


def test_parse_server_inputs_rejects_invalid_port():
    from tools.configure import parse_server_inputs
    with pytest.raises(ValueError, match="port"):
        parse_server_inputs(port="notanumber", timeout="300", max_attempts="3")
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py::test_parse_server_inputs_uses_defaults_for_empty -v
```
Expected: `ImportError`

**Step 3: Implement `parse_server_inputs` and `step_server_config` in `tools/configure.py`**

```python
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

    return {
        "port": _int(port, 8023, "port"),
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
```

**Step 4: Run tests**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add server config step"
```

---

## Task 5: Entity Filter Step (Step 3/5)

Fetches all entities from HA, presents domain checkboxes, then per-domain entity checkboxes. Generates `include_domains` and `exclude_entities` lists.

**Files:**
- Modify: `tools/configure.py`
- Modify: `tests/tools/test_configure.py`

**Step 1: Write failing tests for filter generation logic**

Add to `tests/tools/test_configure.py`:

```python
def test_build_entity_filter_excludes_unselected_within_domain():
    from tools.configure import build_entity_filter
    all_entities = [
        {"entity_id": "light.kitchen"},
        {"entity_id": "light.living_room"},
        {"entity_id": "switch.fan"},
    ]
    selected_domains = ["light"]
    selected_entities = {"light": ["light.kitchen"]}  # living_room NOT selected
    inc_domains, exc_entities = build_entity_filter(all_entities, selected_domains, selected_entities)
    assert inc_domains == ["light"]
    assert "light.living_room" in exc_entities
    assert "light.kitchen" not in exc_entities
    assert "switch.fan" not in exc_entities  # not in selected domain


def test_build_entity_filter_no_exclusions_when_all_selected():
    from tools.configure import build_entity_filter
    all_entities = [{"entity_id": "light.kitchen"}, {"entity_id": "light.hall"}]
    selected_domains = ["light"]
    selected_entities = {"light": ["light.kitchen", "light.hall"]}
    inc_domains, exc_entities = build_entity_filter(all_entities, selected_domains, selected_entities)
    assert inc_domains == ["light"]
    assert exc_entities == []


def test_fetch_entities_from_ha_returns_sorted_list():
    from tools.configure import group_entities_by_domain
    entities = [
        {"entity_id": "switch.fan"},
        {"entity_id": "light.kitchen"},
        {"entity_id": "light.hall"},
    ]
    grouped = group_entities_by_domain(entities)
    assert "light" in grouped
    assert "switch" in grouped
    assert grouped["light"] == sorted(grouped["light"])
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py::test_build_entity_filter_excludes_unselected_within_domain -v
```
Expected: `ImportError`

**Step 3: Implement entity filter helpers and step in `tools/configure.py`**

```python
# ---------------------------------------------------------------------------
# Step 3: Entity Filter
# ---------------------------------------------------------------------------

async def fetch_all_entities(url: str, token: str) -> list[dict]:
    """Fetch all entity states from HA API."""
    import aiohttp
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{url.rstrip('/')}/api/states", headers=headers) as resp:
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
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.shortcuts import checkboxlist_dialog
    from prompt_toolkit.styles import Style

    print("\n" + "=" * 60)
    print("Step 3/5: Entity Filter")
    print("  (Press Enter to skip if HomeAssistant is unavailable)")
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

    # Domain selection
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
        # Pre-select entities NOT in exclude list (i.e., currently included)
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
```

**Step 4: Run tests**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add entity filter step with domain/entity selection"
```

---

## Task 6: User Setup Step (Step 4/5)

Prompts for callsign, calls `tools/setup_totp.py` as subprocess (QR code appears in terminal), captures output to extract the TOTP secret, and writes `users.yaml`.

**Files:**
- Modify: `tools/configure.py`
- Modify: `tests/tools/test_configure.py`

**Step 1: Write failing tests**

Add to `tests/tools/test_configure.py`:

```python
def test_parse_totp_secret_from_output_extracts_secret():
    from tools.configure import parse_totp_secret_from_output
    output = (
        "============================================================\n"
        "Add this to your users.yaml file:\n"
        "============================================================\n"
        '  W1AW: "JBSWY3DPEHPK3PXP"\n'
        "============================================================\n"
    )
    secret = parse_totp_secret_from_output("W1AW", output)
    assert secret == "JBSWY3DPEHPK3PXP"


def test_parse_totp_secret_returns_none_when_not_found():
    from tools.configure import parse_totp_secret_from_output
    secret = parse_totp_secret_from_output("W1AW", "no secret here")
    assert secret is None
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py::test_parse_totp_secret_from_output_extracts_secret -v
```
Expected: `ImportError`

**Step 3: Implement `parse_totp_secret_from_output` and `step_user_setup` in `tools/configure.py`**

```python
# ---------------------------------------------------------------------------
# Step 4: Initial User Setup
# ---------------------------------------------------------------------------

def parse_totp_secret_from_output(callsign: str, output: str) -> str | None:
    """
    Extract TOTP secret from setup_totp.py output.
    Looks for line: '  CALLSIGN: "SECRET"'
    """
    import re
    pattern = rf'^\s+{re.escape(callsign.upper())}:\s+"([A-Z2-7]+)"'
    for line in output.splitlines():
        m = re.match(pattern, line, re.IGNORECASE)
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

    # Run setup_totp.py, capturing output while also displaying it
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
```

**Step 4: Run tests**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add user setup step with TOTP subprocess and users.yaml write"
```

---

## Task 7: Docker Compose Step (Step 5/5)

Prompts for host port and config directory, generates `docker-compose.generated.yml`.

**Files:**
- Modify: `tools/configure.py`
- Modify: `tests/tools/test_configure.py`

**Step 1: Write failing tests**

Add to `tests/tools/test_configure.py`:

```python
def test_generate_compose_uses_provided_port_and_path(tmp_path):
    from tools.configure import generate_compose
    result = generate_compose(host_port=9000, config_dir="/home/user/pqth")
    loaded = yaml.safe_load(result)
    assert "9000:8023" in loaded["services"]["packetqth"]["ports"][0]
    assert "/home/user/pqth/config.yaml" in loaded["services"]["packetqth"]["volumes"][0]


def test_generate_compose_default_port():
    from tools.configure import generate_compose
    result = generate_compose(host_port=8023, config_dir="/opt/pqth")
    loaded = yaml.safe_load(result)
    assert "8023:8023" in loaded["services"]["packetqth"]["ports"][0]
```

**Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_configure.py::test_generate_compose_uses_provided_port_and_path -v
```
Expected: `ImportError`

**Step 3: Implement `generate_compose` and `step_docker_compose` in `tools/configure.py`**

```python
# ---------------------------------------------------------------------------
# Step 5: Docker Compose
# ---------------------------------------------------------------------------

def generate_compose(host_port: int, config_dir: str) -> str:
    """Generate docker-compose YAML string from parameters."""
    compose = {
        "version": "3.8",
        "services": {
            "packetqth": {
                "image": "ghcr.io/ben-kuhn/packetqth:latest",
                "container_name": "packetqth",
                "restart": "unless-stopped",
                "ports": [f"127.0.0.1:{host_port}:8023"],
                "volumes": [
                    f"{config_dir}/config.yaml:/app/config.yaml:ro",
                    f"{config_dir}/users.yaml:/app/users.yaml:ro",
                    f"{config_dir}/logs:/app/logs",
                ],
                "environment": [
                    "- HA_TOKEN=${HA_TOKEN}",
                    "- LOG_LEVEL=${LOG_LEVEL:-INFO}",
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
    default_dir = str(Path.cwd())

    port_str = prompt(HTML(f"Host port to expose telnet on [<ansigreen>{default_port}</ansigreen>]: ")).strip()
    host_port = int(port_str) if port_str.isdigit() else default_port

    config_dir = prompt(HTML(f"Config directory path [<ansigreen>{default_dir}</ansigreen>]: ")).strip() or default_dir

    compose_yaml = generate_compose(host_port=host_port, config_dir=config_dir)
    output_path.write_text(compose_yaml)

    print(f"\n  Written to: {output_path}")
    print("\n  To use it, run:")
    print(f"    mv {output_path.name} docker-compose.yml")
    print("    docker compose up -d")
```

**Step 4: Run tests**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add tools/configure.py tests/tools/test_configure.py
git commit -m "feat: add docker compose generation step"
```

---

## Task 8: Wire the Wizard Together

Add the `main()` function that runs all five steps in sequence.

**Files:**
- Modify: `tools/configure.py`

**Step 1: Add `main()` to `tools/configure.py`**

Replace the existing `if __name__ == "__main__":` block:

```python
# ---------------------------------------------------------------------------
# Main Wizard
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PacketQTH Setup Wizard")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    parser.add_argument("--users", default="users.yaml", help="Path to users.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    env_path = Path(args.env)
    users_path = Path(args.users)
    compose_path = Path("docker-compose.generated.yml")

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
```

**Step 2: Smoke test — run the wizard and verify help output**

```bash
python tools/configure.py --help
```
Expected: prints argparse help with `--config`, `--env`, `--users` options.

**Step 3: Run full test suite**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 4: Commit**

```bash
git add tools/configure.py
git commit -m "feat: wire all wizard steps into main() entry point"
```

---

## Task 9: Update Dockerfile.tools

Add a `CMD` hint for the new wizard and verify the image still builds.

**Files:**
- Modify: `Dockerfile.tools`

**Step 1: Add configure.py to the CMD help text**

In `Dockerfile.tools`, find the `CMD` line and add the configure.py example. The CMD is a single `sh -c` string — add a new line to the echo block:

```
'  Run setup wizard:' && \
echo '    docker run --rm -it -v $(pwd):/app ghcr.io/ben-kuhn/packetqth-tools:latest python tools/configure.py' && \
```

Insert this before the final closing `"`  of the CMD string.

**Step 2: Verify the Dockerfile syntax (no build required)**

```bash
docker build -f Dockerfile.tools -t packetqth-tools-test . --no-cache --progress=plain 2>&1 | tail -5
```
Expected: `Successfully built ...` or equivalent.

**Step 3: Commit**

```bash
git add Dockerfile.tools
git commit -m "feat: add configure.py wizard to tools container CMD help"
```

---

## Task 10: Create `tests/tools/__init__.py`

Without this file pytest can't discover the test module.

**Files:**
- Create: `tests/tools/__init__.py`

**Step 1: Create the file**

```bash
touch tests/tools/__init__.py
```

**Step 2: Verify tests still pass**

```bash
pytest tests/tools/test_configure.py -v
```
Expected: all PASS

**Step 3: Commit**

```bash
git add tests/tools/__init__.py
git commit -m "chore: add tests/tools package init"
```

> **Note:** Do Task 10 first before Task 2 if `tests/tools/` doesn't already exist as a package.

---

## Task Order

1. Task 10 (create `tests/tools/__init__.py`) — do this first
2. Task 1 (add dependency)
3. Task 2 (config I/O helpers + scaffold)
4. Task 3 (HA connection step)
5. Task 4 (server config step)
6. Task 5 (entity filter step)
7. Task 6 (user setup step)
8. Task 7 (docker compose step)
9. Task 8 (wire together)
10. Task 9 (update Dockerfile.tools)
