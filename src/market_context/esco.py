"""ESCO-based occupation and skill normalization.

ESCO is used here as market context and enrichment. It does not provide job
listings, apply URLs, or live vacancy counts.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
import re
from typing import Iterable


DEFAULT_ESCO_SEED_PATH = Path("data/market_context/esco_seed_concepts.csv")


@dataclass(frozen=True)
class EscoConcept:
    """One occupation or skill concept used for local normalization."""

    concept_type: str
    preferred_label: str
    concept_uri: str | None
    broader_group: str | None
    aliases: tuple[str, ...]

    @property
    def all_terms(self) -> tuple[str, ...]:
        """Return preferred label and aliases as searchable terms."""
        return (self.preferred_label, *self.aliases)


class EscoNormalizer:
    """Normalize job titles, occupation groups, and skills with ESCO concepts."""

    source_name = "ESCO occupation and skill taxonomy"
    source_use = "market_context_enrichment"

    def __init__(self, concepts_path: Path | str = DEFAULT_ESCO_SEED_PATH):
        self.concepts_path = Path(concepts_path)
        self.concepts = self._load_concepts(self.concepts_path)
        self._concepts_by_type = {
            concept_type: [
                concept for concept in self.concepts
                if concept.concept_type == concept_type
            ]
            for concept_type in {"occupation", "skill"}
        }

    @staticmethod
    def _normalize(value: object) -> str:
        """Normalize text for matching across labels and aliases."""
        text = str(value or "").lower()
        text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    @staticmethod
    def _tokenize(value: object) -> set[str]:
        return {
            token for token in EscoNormalizer._normalize(value).split()
            if len(token) >= 3
        }

    @staticmethod
    def _load_concepts(path: Path) -> list[EscoConcept]:
        """Load seed concepts from CSV."""
        concepts: list[EscoConcept] = []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                aliases = tuple(
                    alias.strip()
                    for alias in str(row.get("aliases") or "").split(";")
                    if alias.strip()
                )
                concepts.append(EscoConcept(
                    concept_type=str(row["concept_type"]).strip(),
                    preferred_label=str(row["preferred_label"]).strip(),
                    concept_uri=str(row.get("concept_uri") or "").strip() or None,
                    broader_group=str(row.get("broader_group") or "").strip() or None,
                    aliases=aliases,
                ))
        return concepts

    def _matches_concept(self, text: str, concept: EscoConcept) -> bool:
        """Return whether text matches a concept label or alias."""
        normalized_text = self._normalize(text)
        if not normalized_text:
            return False
        text_tokens = self._tokenize(text)
        for term in concept.all_terms:
            normalized_term = self._normalize(term)
            if not normalized_term:
                continue
            if normalized_term in normalized_text:
                return True
            term_tokens = self._tokenize(term)
            if term_tokens and term_tokens.issubset(text_tokens):
                return True
        return False

    def match_concepts(self, text: str, concept_type: str | None = None) -> list[EscoConcept]:
        """Find occupation or skill concepts mentioned in free text."""
        candidates = (
            self._concepts_by_type.get(concept_type, [])
            if concept_type else self.concepts
        )
        return [
            concept for concept in candidates
            if self._matches_concept(text, concept)
        ]

    def normalize_occupation(self, *values: object) -> EscoConcept | None:
        """Return the best occupation concept for title/group text."""
        text = " ".join(str(value or "") for value in values)
        matches = self.match_concepts(text, concept_type="occupation")
        return matches[0] if matches else None

    def normalize_skills(self, skills: Iterable[object] | None) -> list[EscoConcept]:
        """Return matched ESCO skill concepts for a job skill list."""
        concepts: list[EscoConcept] = []
        seen: set[str] = set()
        for skill in skills or []:
            for concept in self.match_concepts(str(skill), concept_type="skill"):
                key = concept.preferred_label.lower()
                if key not in seen:
                    seen.add(key)
                    concepts.append(concept)
        return concepts

    def expand_query_terms(self, query: str) -> list[str]:
        """Expand a query with ESCO preferred labels, aliases, and broader groups."""
        terms = [query, *self._tokenize(query)]
        for concept in self.match_concepts(query):
            terms.extend(concept.all_terms)
            if concept.broader_group:
                terms.append(concept.broader_group)
        return sorted({term.strip().lower() for term in terms if str(term).strip()})

    def search_terms_for_job(self, job: dict) -> list[str]:
        """Return ESCO-enriched terms for one job."""
        terms: list[str] = []
        occupation = self.normalize_occupation(
            job.get("title"),
            job.get("role_type"),
            job.get("occupation_group"),
            job.get("description"),
        )
        if occupation:
            terms.extend(occupation.all_terms)
            if occupation.broader_group:
                terms.append(occupation.broader_group)

        for skill in self.normalize_skills(job.get("required_skills", [])):
            terms.extend(skill.all_terms)
            if skill.broader_group:
                terms.append(skill.broader_group)
        return sorted({term for term in terms if term})

    def normalize_job(self, job: dict) -> dict:
        """Return normalized ESCO context for a job without mutating it."""
        occupation = self.normalize_occupation(
            job.get("title"),
            job.get("role_type"),
            job.get("occupation_group"),
            job.get("description"),
        )
        skills = self.normalize_skills(job.get("required_skills", []))
        return {
            "source": self.source_name,
            "source_use": self.source_use,
            "occupation": self._concept_to_dict(occupation) if occupation else None,
            "skills": [self._concept_to_dict(skill) for skill in skills],
            "search_terms": self.search_terms_for_job(job),
        }

    @staticmethod
    def _concept_to_dict(concept: EscoConcept) -> dict:
        """Serialize a concept for API responses."""
        return {
            "concept_type": concept.concept_type,
            "preferred_label": concept.preferred_label,
            "concept_uri": concept.concept_uri,
            "broader_group": concept.broader_group,
            "aliases": list(concept.aliases),
        }

    def normalize_query(self, query: str) -> dict:
        """Return normalized ESCO context for a search query."""
        occupations = self.match_concepts(query, concept_type="occupation")
        skills = self.match_concepts(query, concept_type="skill")
        return {
            "query": query,
            "source": self.source_name,
            "source_use": self.source_use,
            "occupations": [self._concept_to_dict(concept) for concept in occupations],
            "skills": [self._concept_to_dict(concept) for concept in skills],
            "expanded_terms": self.expand_query_terms(query),
        }
