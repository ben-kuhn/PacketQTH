"""
PacketQTH Entity Filters

Filter HomeAssistant entities by domain, entity ID patterns, and attributes.
"""

from typing import List, Dict, Any, Optional
import fnmatch


class EntityFilter:
    """
    Filter HomeAssistant entities based on configuration.

    Features:
    - Include/exclude by domain (light, switch, sensor, etc.)
    - Exclude specific entities by ID or glob pattern
    - Exclude by attribute values
    """

    def __init__(
        self,
        included_domains: Optional[List[str]] = None,
        excluded_entities: Optional[List[str]] = None,
        excluded_attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize entity filter.

        Args:
            included_domains: List of domains to include (e.g., ['light', 'switch'])
                            If None or empty, all domains are included
            excluded_entities: List of entity IDs or glob patterns to exclude
                             (e.g., ['sensor.uptime', 'sensor.*_last_boot'])
            excluded_attributes: Dict of attributes that cause exclusion
                               (e.g., {'hidden': True, 'disabled': True})
        """
        self.included_domains = set(included_domains) if included_domains else None
        self.excluded_entities = excluded_entities or []
        self.excluded_attributes = excluded_attributes or {}

    def should_include_entity(self, entity: Dict[str, Any]) -> bool:
        """
        Check if an entity should be included based on filters.

        Args:
            entity: Entity dict from HomeAssistant API

        Returns:
            True if entity should be included, False otherwise
        """
        entity_id = entity.get('entity_id', '')
        attributes = entity.get('attributes', {})

        # Extract domain from entity_id (e.g., "light" from "light.kitchen")
        domain = entity_id.split('.')[0] if '.' in entity_id else ''

        # Check domain filter
        if self.included_domains and domain not in self.included_domains:
            return False

        # Check excluded entities (supports glob patterns)
        for pattern in self.excluded_entities:
            if fnmatch.fnmatch(entity_id, pattern):
                return False

        # Check excluded attributes
        for attr_name, excluded_value in self.excluded_attributes.items():
            if attributes.get(attr_name) == excluded_value:
                return False

        return True

    def filter_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of entities.

        Args:
            entities: List of entity dicts from HomeAssistant API

        Returns:
            Filtered list of entities
        """
        return [entity for entity in entities if self.should_include_entity(entity)]

    def get_domains(self, entities: List[Dict[str, Any]]) -> List[str]:
        """
        Get list of unique domains from entities.

        Args:
            entities: List of entity dicts

        Returns:
            Sorted list of unique domains
        """
        domains = set()
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            if '.' in entity_id:
                domain = entity_id.split('.')[0]
                domains.add(domain)
        return sorted(domains)

    def filter_by_domain(
        self,
        entities: List[Dict[str, Any]],
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Filter entities to only include a specific domain.

        Args:
            entities: List of entity dicts
            domain: Domain to filter by (e.g., 'light')

        Returns:
            Filtered list of entities in the specified domain
        """
        return [
            entity for entity in entities
            if entity.get('entity_id', '').startswith(f"{domain}.")
        ]

    @staticmethod
    def from_config(config: Dict[str, Any]) -> 'EntityFilter':
        """
        Create an EntityFilter from configuration dict.

        Expected config format:
        {
            'filters': {
                'included_domains': ['light', 'switch', ...],
                'excluded_entities': ['sensor.uptime', ...],
                'excluded_attributes': {'hidden': True, ...}
            }
        }

        Args:
            config: Configuration dictionary

        Returns:
            EntityFilter instance
        """
        filters_config = config.get('filters', {})

        return EntityFilter(
            included_domains=filters_config.get('included_domains'),
            excluded_entities=filters_config.get('excluded_entities'),
            excluded_attributes=filters_config.get('excluded_attributes')
        )


class EntityMapper:
    """
    Map entities to compact IDs and provide lookup functionality.

    This creates a numeric ID mapping for entities to make packet radio
    commands more compact (e.g., "ON 1" instead of "ON light.kitchen").
    """

    def __init__(self):
        """Initialize entity mapper."""
        self.id_to_entity: Dict[int, Dict[str, Any]] = {}
        self.entity_id_to_id: Dict[str, int] = {}
        self._next_id = 1

    def add_entities(self, entities: List[Dict[str, Any]]) -> None:
        """
        Add entities to the mapper, assigning numeric IDs.

        Args:
            entities: List of entity dicts from HomeAssistant API
        """
        # Sort entities for consistent ID assignment
        sorted_entities = sorted(entities, key=lambda e: e.get('entity_id', ''))

        for entity in sorted_entities:
            entity_id = entity.get('entity_id')
            if not entity_id:
                continue

            # Skip if already mapped
            if entity_id in self.entity_id_to_id:
                continue

            # Assign numeric ID
            numeric_id = self._next_id
            self._next_id += 1

            # Store mappings
            self.id_to_entity[numeric_id] = entity
            self.entity_id_to_id[entity_id] = numeric_id

    def get_by_id(self, numeric_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entity by numeric ID.

        Args:
            numeric_id: Numeric ID assigned to entity

        Returns:
            Entity dict or None if not found
        """
        return self.id_to_entity.get(numeric_id)

    def get_id(self, entity_id: str) -> Optional[int]:
        """
        Get numeric ID for an entity_id.

        Args:
            entity_id: HomeAssistant entity ID (e.g., 'light.kitchen')

        Returns:
            Numeric ID or None if not found
        """
        return self.entity_id_to_id.get(entity_id)

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all mapped entities.

        Returns:
            List of entity dicts sorted by numeric ID
        """
        return [self.id_to_entity[i] for i in sorted(self.id_to_entity.keys())]

    def clear(self) -> None:
        """Clear all mappings."""
        self.id_to_entity.clear()
        self.entity_id_to_id.clear()
        self._next_id = 1

    def refresh(self, entities: List[Dict[str, Any]]) -> None:
        """
        Refresh the mapper with new entity list.

        This clears existing mappings and rebuilds from the provided list.

        Args:
            entities: List of entity dicts from HomeAssistant API
        """
        self.clear()
        self.add_entities(entities)

    def count(self) -> int:
        """
        Get count of mapped entities.

        Returns:
            Number of mapped entities
        """
        return len(self.id_to_entity)
