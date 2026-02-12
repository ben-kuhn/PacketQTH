# PacketQTH HomeAssistant Client

Async HomeAssistant REST API client with entity caching, filtering, and numeric ID mapping.

## Overview

This module provides a Python client for the HomeAssistant REST API designed specifically for PacketQTH's low-bandwidth packet radio use case.

**Key Features:**

- ✅ **Async/await** - Non-blocking I/O with asyncio
- ✅ **Entity caching** - Configurable TTL to reduce API calls
- ✅ **Entity filtering** - Include/exclude by domain, entity ID, or attributes
- ✅ **Numeric ID mapping** - Compact commands (e.g., "ON 1" instead of "ON light.kitchen")
- ✅ **Comprehensive error handling** - Connection, auth, and API errors
- ✅ **Timeout support** - Configurable request timeouts
- ✅ **SSL verification** - Optional for development environments

## Components

### HomeAssistantClient (client.py)

Main API client for interacting with HomeAssistant.

**Basic Usage:**

```python
import asyncio
from homeassistant import HomeAssistantClient

async def main():
    # Create client
    client = HomeAssistantClient(
        url='http://homeassistant.local:8123',
        token='your_long_lived_access_token'
    )

    try:
        # Test connection
        if await client.test_connection():
            print("Connected!")

        # Get all entities
        entities = await client.get_states()
        print(f"Found {len(entities)} entities")

        # Turn on a light
        await client.turn_on('light.kitchen')

        # Turn off a switch
        await client.turn_off('switch.garage')

    finally:
        await client.close()

asyncio.run(main())
```

**With Context Manager:**

```python
async def main():
    async with HomeAssistantClient(url=..., token=...) as client:
        entities = await client.get_states()
        # ... do work ...
    # Client automatically closed
```

**From Configuration:**

```python
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = HomeAssistantClient.from_config(config)
```

### EntityFilter (filters.py)

Filter entities by domain, entity ID patterns, or attributes.

**Example:**

```python
from homeassistant import EntityFilter

# Create filter
entity_filter = EntityFilter(
    included_domains=['light', 'switch', 'sensor'],
    excluded_entities=['sensor.uptime', 'sensor.*_last_boot'],
    excluded_attributes={'hidden': True}
)

# Apply to client
client = HomeAssistantClient(
    url='...',
    token='...',
    entity_filter=entity_filter
)
```

**From Configuration:**

```yaml
# config.yaml
filters:
  included_domains:
    - light
    - switch
    - automation
    - cover
  excluded_entities:
    - sensor.uptime
    - sensor.*_last_boot
  excluded_attributes:
    hidden: true
```

```python
entity_filter = EntityFilter.from_config(config)
```

### EntityMapper (filters.py)

Map entities to numeric IDs for compact packet radio commands.

**Example:**

```python
# Get entities (automatically populates mapper)
entities = await client.get_states()

# Get numeric ID for an entity
numeric_id = client.get_numeric_id('light.kitchen')  # Returns: 1

# Get entity by numeric ID
entity = client.get_entity_by_id(1)  # Returns: {'entity_id': 'light.kitchen', ...}
```

This allows users to type "ON 1" instead of "ON light.kitchen" - critical for slow packet radio connections!

## API Reference

### HomeAssistantClient Methods

#### Connection

```python
async def test_connection() -> bool
```
Test connection to HomeAssistant. Returns True if successful.

```python
async def close()
```
Close HTTP session. Always call this when done, or use context manager.

#### Entity Queries

```python
async def get_states(use_cache: bool = True) -> List[Dict[str, Any]]
```
Get all entity states. Uses cache if valid and `use_cache=True`.

```python
async def get_state(entity_id: str) -> Dict[str, Any]
```
Get state of a specific entity. Always fetches fresh data from API.

```python
async def get_by_domain(domain: str, use_cache: bool = True) -> List[Dict[str, Any]]
```
Get entities filtered by domain (e.g., 'light', 'switch').

```python
async def get_automations(use_cache: bool = True) -> List[Dict[str, Any]]
```
Get all automations.

#### Entity Control

```python
async def turn_on(entity_id: str, **kwargs) -> Dict[str, Any]
```
Turn on an entity. Supports additional parameters like `brightness=255`.

```python
async def turn_off(entity_id: str, **kwargs) -> Dict[str, Any]
```
Turn off an entity.

```python
async def toggle(entity_id: str, **kwargs) -> Dict[str, Any]
```
Toggle an entity's state.

```python
async def set_value(entity_id: str, value: Any, **kwargs) -> Dict[str, Any]
```
Set a value on an entity. Automatically determines the right service based on domain:
- `light`: brightness percentage
- `cover`: position
- `climate`: temperature
- `fan`: percentage
- `input_number`/`number`: value

#### Automations

```python
async def trigger_automation(automation_id: str) -> Dict[str, Any]
```
Trigger an automation.

#### Services (Low-level)

```python
async def call_service(
    domain: str,
    service: str,
    entity_id: Optional[str] = None,
    **service_data
) -> Dict[str, Any]
```
Call any HomeAssistant service. Most users should use the higher-level methods instead.

#### Cache Management

```python
async def refresh_cache() -> int
```
Force refresh of entity cache. Returns number of entities cached.

```python
def invalidate_cache()
```
Mark cache as invalid (next `get_states()` will fetch from API).

```python
def get_cache_age() -> Optional[float]
```
Get age of cache in seconds, or None if no cache.

#### Numeric ID Mapping

```python
def get_entity_by_id(numeric_id: int) -> Optional[Dict[str, Any]]
```
Get entity by numeric ID.

```python
def get_numeric_id(entity_id: str) -> Optional[int]
```
Get numeric ID for an entity_id.

### EntityFilter Methods

```python
def should_include_entity(entity: Dict[str, Any]) -> bool
```
Check if an entity passes the filters.

```python
def filter_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```
Filter a list of entities.

```python
def get_domains(entities: List[Dict[str, Any]]) -> List[str]
```
Get list of unique domains from entities.

```python
def filter_by_domain(entities: List[Dict[str, Any]], domain: str) -> List[Dict[str, Any]]
```
Filter entities to only include a specific domain.

## Configuration

### Complete Example (config.yaml)

```yaml
homeassistant:
  # HomeAssistant URL
  url: http://homeassistant.local:8123

  # Long-lived access token (create in HA profile settings)
  # Can use environment variable: token: ${HA_TOKEN}
  token: eyJ0eXAiOiJKV1QiLCJhbGc...

  # API request timeout in seconds
  timeout: 10

  # Entity cache TTL in seconds
  cache_refresh_interval: 60

  # Verify SSL certificates (set false for self-signed)
  verify_ssl: true

filters:
  # Only include these domains
  included_domains:
    - light
    - switch
    - sensor
    - cover
    - automation

  # Exclude specific entities (supports glob patterns)
  excluded_entities:
    - sensor.uptime
    - sensor.time
    - sensor.*_last_boot

  # Exclude entities with these attributes
  excluded_attributes:
    hidden: true
    disabled: true
```

### Getting a Long-Lived Access Token

1. Open HomeAssistant web interface
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Give it a name (e.g., "PacketQTH")
6. Copy the token immediately (you won't see it again!)

## Error Handling

### Exception Hierarchy

```
HomeAssistantError (base)
├── ConnectionError - Cannot connect to HomeAssistant
├── AuthenticationError - Invalid token (401)
└── NotFoundError - Entity/resource not found (404)
```

### Example Error Handling

```python
from homeassistant import (
    HomeAssistantClient,
    ConnectionError,
    AuthenticationError,
    NotFoundError,
    HomeAssistantError
)

async def safe_control(client, entity_id: str):
    try:
        await client.turn_on(entity_id)
    except AuthenticationError:
        print("Check your HomeAssistant token!")
    except ConnectionError:
        print("Cannot reach HomeAssistant - is it running?")
    except NotFoundError:
        print(f"Entity {entity_id} not found")
    except HomeAssistantError as e:
        print(f"API error: {e}")
```

## Testing

Use the included test tool to verify your HomeAssistant connection:

### Basic Test

```bash
python tools/test_ha.py
```

This will:
- Test connection
- Fetch and display entities
- Show domain filtering
- Test numeric ID mapping

### Test Entity Control

```bash
python tools/test_ha.py --entity light.kitchen
```

This will turn the entity on and off to verify control works.

### Test Automation

```bash
python tools/test_ha.py --automation automation.good_night
```

### Interactive Mode

```bash
python tools/test_ha.py --interactive
```

Interactive commands:
- `list` - List all entities
- `list light` - List lights only
- `get 1` - Get entity #1 details
- `on 1` - Turn entity #1 on
- `off 1` - Turn entity #1 off
- `toggle 1` - Toggle entity #1
- `auto` - List automations
- `trigger 1` - Trigger automation #1
- `refresh` - Refresh entity cache
- `quit` - Exit

## Caching Strategy

### Why Caching?

At 1200 baud, every API call matters:
- Fetching 100 entities ≈ 10KB ≈ 80 seconds @ 1200 baud
- Caching reduces this to once per minute (configurable)

### Cache Behavior

1. **First `get_states()` call** - Fetches from API, populates cache
2. **Subsequent calls (within TTL)** - Returns cached data
3. **After TTL expires** - Next call fetches fresh data
4. **Manual refresh** - Call `refresh_cache()` or `invalidate_cache()`

### Cache vs Fresh Data

```python
# Use cache (fast, may be stale)
entities = await client.get_states(use_cache=True)

# Force fresh fetch (slow, always current)
entities = await client.get_states(use_cache=False)

# Get specific entity (always fresh)
entity = await client.get_state('light.kitchen')
```

**Recommendation:** Use cache for listing, fetch fresh for individual entity status.

## Performance Considerations

### Bandwidth Usage (1200 baud ≈ 120 bytes/sec)

| Operation | Bytes | Time @ 1200 baud |
|-----------|-------|------------------|
| Get all entities (100) | ~10,000 | ~80 seconds |
| Get single entity | ~500 | ~4 seconds |
| Turn on/off | ~200 | ~2 seconds |
| Response | ~100 | ~1 second |

**Optimization Tips:**

1. **Enable caching** - Default 60 second TTL is good
2. **Filter aggressively** - Only include domains you need
3. **Use numeric IDs** - Shorter commands over radio
4. **Batch operations** - If possible, group multiple commands

### Memory Usage

- ~50KB per 100 entities cached
- ~10KB per active session
- Minimal overhead for mapper

## Advanced Usage

### Custom Filtering

```python
# Create custom filter
def my_custom_filter(entity):
    entity_id = entity.get('entity_id', '')

    # Only include entities with "radio" in the name
    if 'radio' not in entity_id.lower():
        return False

    # Only include if state is available
    if entity.get('state') == 'unavailable':
        return False

    return True

# Apply custom filter after fetching
entities = await client.get_states()
filtered = [e for e in entities if my_custom_filter(e)]
```

### Monitoring Cache Performance

```python
# Check cache status
cache_age = client.get_cache_age()
if cache_age:
    print(f"Cache is {cache_age:.1f} seconds old")
else:
    print("No cache")

# Track cache hits
entities = await client.get_states(use_cache=True)
if client.get_cache_age() < 1:
    print("Cache miss - fetched from API")
else:
    print("Cache hit")
```

### Reconnection Logic

```python
async def resilient_operation(client):
    max_retries = 3

    for attempt in range(max_retries):
        try:
            return await client.get_states()
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"Connection failed, retrying...")
                await asyncio.sleep(5)
            else:
                raise
```

## HomeAssistant API Reference

For complete API documentation, see:
- [HomeAssistant REST API](https://developers.home-assistant.io/docs/api/rest/)

### Common Endpoints

- `GET /api/` - API information
- `GET /api/states` - All entity states
- `GET /api/states/<entity_id>` - Single entity state
- `POST /api/services/<domain>/<service>` - Call service
- `GET /api/config` - Configuration info

## Troubleshooting

### "Cannot connect to HomeAssistant"

1. Check URL is correct
2. Verify HomeAssistant is running
3. Check firewall/network connectivity
4. Try `curl http://homeassistant.local:8123/api/` in browser

### "Invalid HomeAssistant token"

1. Generate new long-lived access token in HA
2. Update config.yaml or environment variable
3. Verify token has no extra whitespace

### "Request timeout"

1. Increase timeout in config: `timeout: 30`
2. Check HomeAssistant is not overloaded
3. Check network latency

### Empty entity list after filtering

1. Check `included_domains` in config
2. Verify domains exist: `await client.get_by_domain('light')`
3. Disable filters temporarily to see all entities

### SSL certificate errors

For development/self-signed certs:
```yaml
homeassistant:
  verify_ssl: false
```

**Warning:** Only disable SSL verification in trusted networks!

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/test_homeassistant.py
```

### Adding New Features

1. Add method to `HomeAssistantClient`
2. Add test to `tools/test_ha.py`
3. Update this README
4. Update main ARCHITECTURE.md if significant

## Further Reading

- [HomeAssistant REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

**73!** 📡🏠
