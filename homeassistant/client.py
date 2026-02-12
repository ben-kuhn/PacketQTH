"""
PacketQTH HomeAssistant API Client

Async HTTP client for HomeAssistant REST API with entity caching and filtering.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from .filters import EntityFilter, EntityMapper


logger = logging.getLogger(__name__)


class HomeAssistantError(Exception):
    """Base exception for HomeAssistant API errors"""
    pass


class ConnectionError(HomeAssistantError):
    """Connection to HomeAssistant failed"""
    pass


class AuthenticationError(HomeAssistantError):
    """Authentication failed (invalid token)"""
    pass


class NotFoundError(HomeAssistantError):
    """Entity or resource not found"""
    pass


class HomeAssistantClient:
    """
    Async client for HomeAssistant REST API.

    Features:
    - Entity caching with TTL
    - Configurable filtering
    - Numeric ID mapping for compact commands
    - Comprehensive error handling
    - Timeout support
    """

    def __init__(
        self,
        url: str,
        token: str,
        entity_filter: Optional[EntityFilter] = None,
        timeout: int = 10,
        cache_ttl: int = 60,
        verify_ssl: bool = True
    ):
        """
        Initialize HomeAssistant client.

        Args:
            url: HomeAssistant base URL (e.g., 'http://homeassistant.local:8123')
            token: Long-lived access token
            entity_filter: Optional EntityFilter for filtering entities
            timeout: Request timeout in seconds (default: 10)
            cache_ttl: Entity cache time-to-live in seconds (default: 60)
            verify_ssl: Verify SSL certificates (default: True)
        """
        self.url = url.rstrip('/')
        self.token = token
        self.entity_filter = entity_filter or EntityFilter()
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.verify_ssl = verify_ssl

        # Entity cache
        self._entity_cache: List[Dict[str, Any]] = []
        self._cache_timestamp: Optional[datetime] = None

        # Entity mapper (numeric IDs)
        self.mapper = EntityMapper()

        # HTTP session (created on first use)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
            )
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _is_cache_valid(self) -> bool:
        """Check if entity cache is still valid."""
        if not self._cache_timestamp:
            return False

        age = datetime.now() - self._cache_timestamp
        return age.total_seconds() < self.cache_ttl

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Any]:
        """
        Make HTTP request to HomeAssistant API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/states')
            json_data: Optional JSON data for POST requests

        Returns:
            Tuple of (status_code, response_data)

        Raises:
            ConnectionError: Failed to connect
            AuthenticationError: Invalid token
            HomeAssistantError: Other API errors
        """
        url = f"{self.url}{endpoint}"

        try:
            session = await self._get_session()

            async with session.request(method, url, json=json_data) as response:
                status = response.status

                # Try to parse JSON response
                try:
                    data = await response.json()
                except Exception:
                    data = await response.text()

                # Handle error status codes
                if status == 401:
                    logger.error(f"Authentication failed: Invalid token")
                    raise AuthenticationError("Invalid HomeAssistant token")

                elif status == 404:
                    logger.error(f"Not found: {endpoint}")
                    raise NotFoundError(f"Resource not found: {endpoint}")

                elif status >= 400:
                    logger.error(f"API error {status}: {data}")
                    raise HomeAssistantError(f"API error {status}: {data}")

                return status, data

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Cannot connect to HomeAssistant: {e}")

        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {endpoint}")
            raise ConnectionError(f"Request timeout: {endpoint}")

        except (AuthenticationError, NotFoundError, HomeAssistantError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HomeAssistantError(f"Unexpected error: {e}")

    async def test_connection(self) -> bool:
        """
        Test connection to HomeAssistant.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self._request('GET', '/api/')
            logger.info("Connection to HomeAssistant successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def get_states(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all entity states from HomeAssistant.

        Args:
            use_cache: Use cached entities if available (default: True)

        Returns:
            List of entity dicts (filtered)

        Raises:
            ConnectionError: Failed to connect
            AuthenticationError: Invalid token
            HomeAssistantError: Other API errors
        """
        # Return cached entities if valid
        if use_cache and self._is_cache_valid():
            logger.debug(f"Using cached entities ({len(self._entity_cache)} entities)")
            return self._entity_cache

        # Fetch from API
        logger.info("Fetching entities from HomeAssistant")
        status, data = await self._request('GET', '/api/states')

        if not isinstance(data, list):
            raise HomeAssistantError("Invalid response format: expected list")

        # Apply filters
        filtered_entities = self.entity_filter.filter_entities(data)

        # Update cache
        self._entity_cache = filtered_entities
        self._cache_timestamp = datetime.now()

        # Update mapper
        self.mapper.refresh(filtered_entities)

        logger.info(
            f"Fetched {len(data)} entities, "
            f"filtered to {len(filtered_entities)}"
        )

        return filtered_entities

    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """
        Get state of a specific entity.

        Args:
            entity_id: HomeAssistant entity ID (e.g., 'light.kitchen')

        Returns:
            Entity state dict

        Raises:
            NotFoundError: Entity not found
            ConnectionError: Failed to connect
            HomeAssistantError: Other API errors
        """
        logger.debug(f"Getting state for {entity_id}")
        status, data = await self._request('GET', f'/api/states/{entity_id}')

        return data

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **service_data
    ) -> Dict[str, Any]:
        """
        Call a HomeAssistant service.

        Args:
            domain: Service domain (e.g., 'light', 'switch')
            service: Service name (e.g., 'turn_on', 'turn_off')
            entity_id: Optional entity ID to target
            **service_data: Additional service data (e.g., brightness=255)

        Returns:
            Service call response

        Raises:
            ConnectionError: Failed to connect
            HomeAssistantError: Service call failed
        """
        endpoint = f'/api/services/{domain}/{service}'

        # Build service data
        data = {}
        if entity_id:
            data['entity_id'] = entity_id
        data.update(service_data)

        logger.info(f"Calling service {domain}.{service} with data: {data}")

        status, response = await self._request('POST', endpoint, json_data=data)

        return response

    async def turn_on(
        self,
        entity_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Turn on an entity.

        Args:
            entity_id: Entity ID (e.g., 'light.kitchen')
            **kwargs: Additional parameters (e.g., brightness=255, rgb_color=[255,0,0])

        Returns:
            Service call response
        """
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'turn_on', entity_id=entity_id, **kwargs)

    async def turn_off(
        self,
        entity_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Turn off an entity.

        Args:
            entity_id: Entity ID (e.g., 'light.kitchen')
            **kwargs: Additional parameters

        Returns:
            Service call response
        """
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'turn_off', entity_id=entity_id, **kwargs)

    async def toggle(
        self,
        entity_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Toggle an entity.

        Args:
            entity_id: Entity ID (e.g., 'light.kitchen')
            **kwargs: Additional parameters

        Returns:
            Service call response
        """
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'toggle', entity_id=entity_id, **kwargs)

    async def set_value(
        self,
        entity_id: str,
        value: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Set a value on an entity (brightness, position, temperature, etc.).

        Args:
            entity_id: Entity ID
            value: Value to set (meaning depends on entity type)
            **kwargs: Additional parameters

        Returns:
            Service call response
        """
        domain = entity_id.split('.')[0]

        # Map value to appropriate service parameter based on domain
        service_data = kwargs.copy()

        if domain == 'light':
            service_data['brightness_pct'] = value
            service = 'turn_on'
        elif domain == 'cover':
            service_data['position'] = value
            service = 'set_cover_position'
        elif domain == 'climate':
            service_data['temperature'] = value
            service = 'set_temperature'
        elif domain == 'fan':
            service_data['percentage'] = value
            service = 'set_percentage'
        elif domain in ('input_number', 'number'):
            service_data['value'] = value
            service = 'set_value'
        else:
            raise HomeAssistantError(
                f"Don't know how to set value for domain '{domain}'"
            )

        return await self.call_service(domain, service, entity_id=entity_id, **service_data)

    async def trigger_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Trigger an automation.

        Args:
            automation_id: Automation entity ID (e.g., 'automation.good_night')

        Returns:
            Service call response
        """
        return await self.call_service(
            'automation',
            'trigger',
            entity_id=automation_id
        )

    async def get_automations(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all automations.

        Args:
            use_cache: Use cached entities if available (default: True)

        Returns:
            List of automation entities
        """
        entities = await self.get_states(use_cache=use_cache)
        return [e for e in entities if e.get('entity_id', '').startswith('automation.')]

    async def get_by_domain(
        self,
        domain: str,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get entities by domain.

        Args:
            domain: Domain to filter by (e.g., 'light', 'switch')
            use_cache: Use cached entities if available (default: True)

        Returns:
            List of entities in the specified domain
        """
        entities = await self.get_states(use_cache=use_cache)
        return [e for e in entities if e.get('entity_id', '').startswith(f'{domain}.')]

    async def refresh_cache(self) -> int:
        """
        Force refresh of entity cache.

        Returns:
            Number of entities in cache after refresh
        """
        entities = await self.get_states(use_cache=False)
        return len(entities)

    def get_entity_by_id(self, numeric_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entity by numeric ID (from mapper).

        Args:
            numeric_id: Numeric ID assigned to entity

        Returns:
            Entity dict or None if not found
        """
        return self.mapper.get_by_id(numeric_id)

    def get_numeric_id(self, entity_id: str) -> Optional[int]:
        """
        Get numeric ID for an entity_id.

        Args:
            entity_id: HomeAssistant entity ID

        Returns:
            Numeric ID or None if not found
        """
        return self.mapper.get_id(entity_id)

    def get_cache_age(self) -> Optional[float]:
        """
        Get age of entity cache in seconds.

        Returns:
            Cache age in seconds, or None if no cache
        """
        if not self._cache_timestamp:
            return None

        age = datetime.now() - self._cache_timestamp
        return age.total_seconds()

    def invalidate_cache(self):
        """Invalidate entity cache (force refresh on next get_states())."""
        self._cache_timestamp = None
        logger.debug("Entity cache invalidated")

    @staticmethod
    def from_config(config: Dict[str, Any]) -> 'HomeAssistantClient':
        """
        Create HomeAssistantClient from configuration dict.

        Expected config format:
        {
            'homeassistant': {
                'url': 'http://homeassistant.local:8123',
                'token': 'your_token_here',
                'timeout': 10,
                'cache_refresh_interval': 60,
                'verify_ssl': True
            },
            'filters': {
                'included_domains': ['light', 'switch', ...],
                'excluded_entities': [...],
                'excluded_attributes': {...}
            }
        }

        Args:
            config: Configuration dictionary

        Returns:
            HomeAssistantClient instance
        """
        ha_config = config.get('homeassistant', {})

        # Create entity filter from config
        entity_filter = EntityFilter.from_config(config)

        return HomeAssistantClient(
            url=ha_config.get('url', 'http://localhost:8123'),
            token=ha_config.get('token', ''),
            entity_filter=entity_filter,
            timeout=ha_config.get('timeout', 10),
            cache_ttl=ha_config.get('cache_refresh_interval', 60),
            verify_ssl=ha_config.get('verify_ssl', True)
        )
