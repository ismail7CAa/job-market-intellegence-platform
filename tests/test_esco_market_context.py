"""Tests for ESCO market-context normalization."""

from src.market_context import EscoNormalizer


def test_esco_normalizer_maps_occupation_aliases():
    """Occupation aliases should normalize to a stable concept."""
    normalizer = EscoNormalizer()

    payload = normalizer.normalize_query("nursing jobs in Berlin")

    assert payload["source_use"] == "market_context_enrichment"
    assert payload["occupations"][0]["preferred_label"] == "Nurse"
    assert "nurse" in payload["expanded_terms"]


def test_esco_normalizer_maps_german_skill_aliases():
    """German skill aliases should expand to the canonical skill label."""
    normalizer = EscoNormalizer()

    payload = normalizer.normalize_query("Staplerfahrer Lager")

    assert any(skill["preferred_label"] == "Forklift" for skill in payload["skills"])
    assert "forklift" in payload["expanded_terms"]


def test_esco_normalizer_enriches_job_search_terms():
    """Job enrichment should include occupation and skill search terms."""
    normalizer = EscoNormalizer()

    terms = normalizer.search_terms_for_job({
        "title": "Accountant",
        "occupation_group": "Accounting and Finance",
        "required_skills": ["DATEV", "Excel"],
    })

    assert "Accountant" in terms
    assert "Buchhaltung" in terms
    assert "DATEV" in terms
