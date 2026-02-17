"""
Tests for homeassistant/filters.py

Covers: EntityFilter (all methods), EntityMapper (all methods)
"""

import pytest
from homeassistant.filters import EntityFilter, EntityMapper


def make_entity(entity_id, state='on', **attrs):
    return {'entity_id': entity_id, 'state': state, 'attributes': attrs}


# ---------------------------------------------------------------------------
# EntityFilter tests
# ---------------------------------------------------------------------------

class TestEntityFilter:

    # -- should_include_entity --

    def test_no_filters_includes_everything(self):
        ef = EntityFilter()
        assert ef.should_include_entity(make_entity('light.kitchen'))
        assert ef.should_include_entity(make_entity('sensor.temp'))

    def test_included_domains_allows_matching(self):
        ef = EntityFilter(included_domains=['light'])
        assert ef.should_include_entity(make_entity('light.kitchen'))

    def test_included_domains_rejects_non_matching(self):
        ef = EntityFilter(included_domains=['light'])
        assert not ef.should_include_entity(make_entity('sensor.temp'))

    def test_included_domains_multiple(self):
        ef = EntityFilter(included_domains=['light', 'switch'])
        assert ef.should_include_entity(make_entity('light.kitchen'))
        assert ef.should_include_entity(make_entity('switch.garage'))
        assert not ef.should_include_entity(make_entity('sensor.temp'))

    def test_excluded_entities_exact_match(self):
        ef = EntityFilter(excluded_entities=['sensor.uptime'])
        assert not ef.should_include_entity(make_entity('sensor.uptime'))
        assert ef.should_include_entity(make_entity('sensor.temperature'))

    def test_excluded_entities_glob_wildcard(self):
        ef = EntityFilter(excluded_entities=['sensor.*_boot'])
        assert not ef.should_include_entity(make_entity('sensor.last_boot'))
        assert ef.should_include_entity(make_entity('sensor.temperature'))

    def test_excluded_entities_star_glob(self):
        ef = EntityFilter(excluded_entities=['sensor.*'])
        assert not ef.should_include_entity(make_entity('sensor.temp'))
        assert ef.should_include_entity(make_entity('light.kitchen'))

    def test_excluded_attributes_excludes_matching(self):
        ef = EntityFilter(excluded_attributes={'hidden': True})
        assert not ef.should_include_entity(make_entity('light.hidden', hidden=True))

    def test_excluded_attributes_allows_non_matching(self):
        ef = EntityFilter(excluded_attributes={'hidden': True})
        assert ef.should_include_entity(make_entity('light.visible'))

    def test_excluded_attributes_checks_value(self):
        ef = EntityFilter(excluded_attributes={'hidden': True})
        # hidden=False should NOT be excluded
        assert ef.should_include_entity(make_entity('light.x', hidden=False))

    def test_domain_and_excluded_combined(self):
        ef = EntityFilter(
            included_domains=['light'],
            excluded_entities=['light.hidden']
        )
        assert ef.should_include_entity(make_entity('light.kitchen'))
        assert not ef.should_include_entity(make_entity('light.hidden'))
        assert not ef.should_include_entity(make_entity('switch.garage'))

    def test_entity_without_entity_id(self):
        ef = EntityFilter()
        # Should not crash on entity with no entity_id
        assert ef.should_include_entity({'state': 'on', 'attributes': {}})

    def test_entity_without_dot_in_id(self):
        ef = EntityFilter(included_domains=['light'])
        # entity_id with no dot - domain = ''
        assert not ef.should_include_entity({'entity_id': 'nodot', 'state': 'on', 'attributes': {}})

    # -- filter_entities --

    def test_filter_entities_returns_matching(self, sample_entities):
        ef = EntityFilter(included_domains=['light'])
        result = ef.filter_entities(sample_entities)
        assert all(e['entity_id'].startswith('light.') for e in result)
        assert len(result) == 2  # kitchen + bedroom

    def test_filter_entities_empty_list(self):
        ef = EntityFilter(included_domains=['light'])
        assert ef.filter_entities([]) == []

    def test_filter_entities_no_filters(self, sample_entities):
        ef = EntityFilter()
        result = ef.filter_entities(sample_entities)
        assert len(result) == len(sample_entities)

    # -- get_domains --

    def test_get_domains_returns_sorted_unique(self, sample_entities):
        ef = EntityFilter()
        domains = ef.get_domains(sample_entities)
        assert domains == sorted(set(domains))  # sorted and unique

    def test_get_domains_correct_extraction(self, sample_entities):
        ef = EntityFilter()
        domains = ef.get_domains(sample_entities)
        assert 'light' in domains
        assert 'switch' in domains
        assert 'sensor' in domains

    def test_get_domains_empty_list(self):
        ef = EntityFilter()
        assert ef.get_domains([]) == []

    def test_get_domains_skips_no_dot(self):
        ef = EntityFilter()
        entities = [{'entity_id': 'nodot', 'state': 'on', 'attributes': {}}]
        assert ef.get_domains(entities) == []

    # -- filter_by_domain --

    def test_filter_by_domain(self, sample_entities):
        ef = EntityFilter()
        lights = ef.filter_by_domain(sample_entities, 'light')
        assert all(e['entity_id'].startswith('light.') for e in lights)

    def test_filter_by_domain_no_match(self, sample_entities):
        ef = EntityFilter()
        result = ef.filter_by_domain(sample_entities, 'media_player')
        assert result == []

    def test_filter_by_domain_empty_list(self):
        ef = EntityFilter()
        assert ef.filter_by_domain([], 'light') == []

    # -- from_config --

    def test_from_config_full(self):
        config = {
            'filters': {
                'included_domains': ['light', 'switch'],
                'excluded_entities': ['sensor.uptime'],
                'excluded_attributes': {'hidden': True}
            }
        }
        ef = EntityFilter.from_config(config)
        assert ef.included_domains == {'light', 'switch'}
        assert 'sensor.uptime' in ef.excluded_entities
        assert ef.excluded_attributes == {'hidden': True}

    def test_from_config_empty(self):
        ef = EntityFilter.from_config({})
        assert ef.included_domains is None
        assert ef.excluded_entities == []
        assert ef.excluded_attributes == {}


# ---------------------------------------------------------------------------
# EntityMapper tests
# ---------------------------------------------------------------------------

class TestEntityMapper:

    def test_add_entities_assigns_ids(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        assert em.count() == len(sample_entities)

    def test_get_by_id_returns_entity(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        entity = em.get_by_id(1)
        assert entity is not None
        assert 'entity_id' in entity

    def test_get_by_id_nonexistent(self):
        em = EntityMapper()
        assert em.get_by_id(999) is None

    def test_get_id_returns_numeric(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        entity_id = sample_entities[0]['entity_id']
        numeric = em.get_id(entity_id)
        assert isinstance(numeric, int)
        assert numeric >= 1

    def test_get_id_nonexistent(self):
        em = EntityMapper()
        assert em.get_id('light.nonexistent') is None

    def test_ids_are_consistent(self, sample_entities):
        """Round-trip: get numeric id → get entity → entity_id matches."""
        em = EntityMapper()
        em.add_entities(sample_entities)
        for entity in sample_entities:
            eid = entity['entity_id']
            numeric = em.get_id(eid)
            assert numeric is not None
            retrieved = em.get_by_id(numeric)
            assert retrieved['entity_id'] == eid

    def test_ids_sorted_alphabetically(self):
        """Entities are assigned IDs in alphabetical order."""
        entities = [
            make_entity('light.z_last'),
            make_entity('light.a_first'),
            make_entity('light.m_middle'),
        ]
        em = EntityMapper()
        em.add_entities(entities)
        assert em.get_id('light.a_first') == 1
        assert em.get_id('light.m_middle') == 2
        assert em.get_id('light.z_last') == 3

    def test_get_all_returns_all(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        all_entities = em.get_all()
        assert len(all_entities) == len(sample_entities)

    def test_get_all_sorted_by_id(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        all_entities = em.get_all()
        ids = [em.get_id(e['entity_id']) for e in all_entities]
        assert ids == sorted(ids)

    def test_count(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        assert em.count() == len(sample_entities)

    def test_count_empty(self):
        em = EntityMapper()
        assert em.count() == 0

    def test_clear(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        em.clear()
        assert em.count() == 0
        assert em.get_by_id(1) is None

    def test_clear_resets_next_id(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        em.clear()
        em.add_entities([make_entity('light.kitchen')])
        assert em.get_id('light.kitchen') == 1

    def test_refresh_replaces_entities(self, sample_entities):
        em = EntityMapper()
        em.add_entities(sample_entities)
        new_entities = [make_entity('light.new_only')]
        em.refresh(new_entities)
        assert em.count() == 1
        assert em.get_id('light.new_only') == 1
        # Old entities gone
        assert em.get_id('light.kitchen') is None

    def test_add_entities_skips_duplicates(self):
        em = EntityMapper()
        entities = [make_entity('light.kitchen')]
        em.add_entities(entities)
        em.add_entities(entities)  # Add again
        assert em.count() == 1

    def test_add_entities_skips_missing_entity_id(self):
        em = EntityMapper()
        em.add_entities([{'state': 'on', 'attributes': {}}])
        assert em.count() == 0
