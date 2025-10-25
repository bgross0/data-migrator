"""
Identity Resolution Service.

Implements 3-layer matching strategy from MATCHING_POLICY.md:
1. Deterministic (exact natural key match)
2. Probabilistic (similarity scoring)
3. HITL (human-in-the-loop for ambiguous cases)
"""
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from datetime import date
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from app.core.normalization import (
    Normalizer,
    NaturalKeyGenerator,
    ContentHasher
)


class MatchCandidate:
    """Represents a potential match with confidence score."""

    def __init__(self, record_id: int, record_data: Dict[str, Any], score: float, match_logic: str):
        self.record_id = record_id
        self.record_data = record_data
        self.score = score
        self.match_logic = match_logic


class MatchResult:
    """Result of identity resolution."""

    def __init__(
        self,
        matched: bool,
        record_id: Optional[int] = None,
        confidence: float = 0.0,
        action: str = 'no_match',
        candidates: Optional[List[MatchCandidate]] = None,
        quarantine_reason: Optional[str] = None
    ):
        self.matched = matched
        self.record_id = record_id
        self.confidence = confidence
        self.action = action  # 'exact_match', 'fuzzy_match', 'no_match', 'multi_match', 'create'
        self.candidates = candidates or []
        self.quarantine_reason = quarantine_reason


class IdentityResolutionService:
    """
    Resolves entity identity using deterministic + probabilistic + HITL.

    Implements matching strategies from MATCHING_POLICY.md.
    """

    def __init__(self, db: Session):
        self.db = db

    def resolve_partner_company(
        self,
        vat: Optional[str] = None,
        name: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state_code: Optional[str] = None,
        country_code: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company_id: Optional[int] = None
    ) -> MatchResult:
        """
        Resolve company partner identity.

        Layer 1: Deterministic (VAT or name+address or name+contact)
        Layer 2: Probabilistic (name similarity + address similarity)
        Layer 3: HITL if multi-match

        From MATCHING_POLICY.md thresholds:
        - Auto-match: ≥0.85
        - HITL: 0.70-0.85
        - Auto-reject: <0.70

        Args:
            vat: VAT number
            name: Company name
            street: Street address
            city: City
            state_code: State code
            country_code: Country code
            phone: Phone number
            email: Email address
            company_id: Company scope

        Returns:
            MatchResult
        """
        # Generate natural key
        natural_key = NaturalKeyGenerator.generate_partner_company_key(
            vat=vat,
            name=name,
            street=street,
            city=city,
            state_code=state_code,
            country_code=country_code,
            phone=phone,
            email=email
        )

        # Layer 1: Deterministic lookup (would query canonical dim_partner table)
        # For now, return structure showing logic
        # In production: SELECT * FROM dim_partner WHERE natural_key_hash = :natural_key

        deterministic_match = self._deterministic_lookup('dim_partner', natural_key, company_id)
        if deterministic_match:
            return MatchResult(
                matched=True,
                record_id=deterministic_match['partner_sk'],
                confidence=1.0,
                action='exact_match'
            )

        # Layer 2: Probabilistic matching
        if name:
            candidates = self._fuzzy_match_company(
                name=name,
                street=street,
                city=city,
                company_id=company_id
            )

            # Filter by threshold
            auto_match = [c for c in candidates if c.score >= 0.85]
            hitl_candidates = [c for c in candidates if 0.70 <= c.score < 0.85]

            if len(auto_match) == 1:
                # Single high-confidence match
                return MatchResult(
                    matched=True,
                    record_id=auto_match[0].record_id,
                    confidence=auto_match[0].score,
                    action='fuzzy_match',
                    candidates=auto_match
                )

            if len(auto_match) > 1:
                # Multi-match: HITL required
                return MatchResult(
                    matched=False,
                    confidence=max(c.score for c in auto_match),
                    action='multi_match',
                    candidates=auto_match,
                    quarantine_reason=f'{len(auto_match)} candidates with score ≥0.85'
                )

            if hitl_candidates:
                # Medium confidence: HITL
                return MatchResult(
                    matched=False,
                    confidence=max(c.score for c in hitl_candidates),
                    action='multi_match',
                    candidates=hitl_candidates,
                    quarantine_reason=f'{len(hitl_candidates)} candidates in HITL range (0.70-0.85)'
                )

        # Layer 3: No match found
        return MatchResult(
            matched=False,
            confidence=0.0,
            action='create'
        )

    def resolve_partner_contact(
        self,
        parent_id: int,
        full_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> MatchResult:
        """
        Resolve contact (person) identity.

        Must have same parent company (hard constraint).

        From MATCHING_POLICY.md thresholds:
        - Auto-match: ≥0.80
        - HITL: 0.65-0.80
        - Auto-reject: <0.65

        Args:
            parent_id: Parent company partner_sk
            full_name: Full name
            email: Email address
            phone: Phone number

        Returns:
            MatchResult
        """
        # Generate natural key
        natural_key = NaturalKeyGenerator.generate_partner_contact_key(
            parent_id=parent_id,
            full_name=full_name,
            email=email,
            phone=phone
        )

        # Layer 1: Deterministic
        deterministic_match = self._deterministic_lookup(
            'dim_partner',
            natural_key,
            None,
            filters={'parent_sk': parent_id}
        )

        if deterministic_match:
            return MatchResult(
                matched=True,
                record_id=deterministic_match['partner_sk'],
                confidence=1.0,
                action='exact_match'
            )

        # Layer 2: Probabilistic (within same parent only)
        candidates = self._fuzzy_match_contact(
            parent_id=parent_id,
            full_name=full_name,
            email=email
        )

        auto_match = [c for c in candidates if c.score >= 0.80]
        hitl_candidates = [c for c in candidates if 0.65 <= c.score < 0.80]

        if len(auto_match) == 1:
            return MatchResult(
                matched=True,
                record_id=auto_match[0].record_id,
                confidence=auto_match[0].score,
                action='fuzzy_match',
                candidates=auto_match
            )

        if auto_match or hitl_candidates:
            all_candidates = auto_match if auto_match else hitl_candidates
            return MatchResult(
                matched=False,
                confidence=max(c.score for c in all_candidates),
                action='multi_match',
                candidates=all_candidates,
                quarantine_reason=f'{len(all_candidates)} contact candidates'
            )

        return MatchResult(matched=False, confidence=0.0, action='create')

    def resolve_lead(
        self,
        external_id: Optional[str] = None,
        partner_id: Optional[int] = None,
        name: Optional[str] = None,
        email_from: Optional[str] = None,
        create_date: Optional[date] = None
    ) -> MatchResult:
        """
        Resolve CRM lead identity.

        From MATCHING_POLICY.md thresholds:
        - Auto-match: ≥0.75
        - HITL: 0.60-0.75
        - Auto-reject: <0.60

        Args:
            external_id: External ID from source
            partner_id: Partner SK
            name: Lead name
            email_from: Email
            create_date: Creation date

        Returns:
            MatchResult
        """
        # Generate natural key
        natural_key = NaturalKeyGenerator.generate_lead_key(
            external_id=external_id,
            partner_id=partner_id,
            name=name,
            email_from=email_from,
            create_date=create_date
        )

        # Layer 1: Deterministic
        deterministic_match = self._deterministic_lookup('fact_lead', natural_key, None)

        if deterministic_match:
            return MatchResult(
                matched=True,
                record_id=deterministic_match['lead_sk'],
                confidence=1.0,
                action='exact_match'
            )

        # Layer 2: Probabilistic
        if name and email_from:
            candidates = self._fuzzy_match_lead(
                name=name,
                email_from=email_from,
                create_date=create_date
            )

            auto_match = [c for c in candidates if c.score >= 0.75]
            hitl_candidates = [c for c in candidates if 0.60 <= c.score < 0.75]

            if len(auto_match) == 1:
                return MatchResult(
                    matched=True,
                    record_id=auto_match[0].record_id,
                    confidence=auto_match[0].score,
                    action='fuzzy_match',
                    candidates=auto_match
                )

            if auto_match or hitl_candidates:
                all_candidates = auto_match if auto_match else hitl_candidates
                return MatchResult(
                    matched=False,
                    confidence=max(c.score for c in all_candidates),
                    action='multi_match',
                    candidates=all_candidates,
                    quarantine_reason=f'{len(all_candidates)} lead candidates'
                )

        return MatchResult(matched=False, confidence=0.0, action='create')

    def _deterministic_lookup(
        self,
        table: str,
        natural_key_hash: str,
        company_id: Optional[int],
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform deterministic lookup by natural key hash.

        In production, this queries the canonical schema tables.

        Args:
            table: Table name (dim_partner, fact_lead, etc.)
            natural_key_hash: MD5 hash of natural key
            company_id: Company scope
            filters: Additional filters

        Returns:
            Record dict or None
        """
        # TODO: Implement actual DB query against canonical schema
        # Example:
        # SELECT * FROM {table}
        # WHERE natural_key_hash = :natural_key_hash
        #   AND (company_sk = :company_id OR :company_id IS NULL)
        #   AND {additional_filters}
        # LIMIT 1

        return None  # Placeholder for now

    def _fuzzy_match_company(
        self,
        name: str,
        street: Optional[str],
        city: Optional[str],
        company_id: Optional[int]
    ) -> List[MatchCandidate]:
        """
        Fuzzy match company by name + address similarity.

        From MATCHING_POLICY.md:
        - Name similarity: Jaro-Winkler (70% weight)
        - Address similarity: Levenshtein (30% weight)

        Args:
            name: Company name
            street: Street address
            city: City
            company_id: Company scope

        Returns:
            List of match candidates with scores
        """
        normalized_name = Normalizer.normalize_company_name(name)

        # TODO: Query candidates from dim_partner
        # WHERE company_sk = :company_id (if scoped)
        candidates_from_db = []  # Placeholder

        results = []
        for candidate in candidates_from_db:
            # Name similarity (Jaro-Winkler)
            candidate_name = Normalizer.normalize_company_name(candidate['name'])
            name_score = Levenshtein.jaro_winkler(normalized_name, candidate_name)

            # Address similarity (Levenshtein)
            if street and city and candidate.get('street') and candidate.get('city'):
                source_addr = f"{street} {city}".lower()
                candidate_addr = f"{candidate['street']} {candidate['city']}".lower()
                addr_score = Levenshtein.normalized_similarity(source_addr, candidate_addr)
            else:
                addr_score = 0.0

            # Combined score
            combined = 0.7 * name_score + 0.3 * addr_score

            results.append(MatchCandidate(
                record_id=candidate['partner_sk'],
                record_data=candidate,
                score=combined,
                match_logic=f"name:{name_score:.2f} addr:{addr_score:.2f}"
            ))

        # Sort by score descending
        results.sort(key=lambda c: c.score, reverse=True)

        return results

    def _fuzzy_match_contact(
        self,
        parent_id: int,
        full_name: str,
        email: Optional[str]
    ) -> List[MatchCandidate]:
        """
        Fuzzy match contact within same parent company.

        From MATCHING_POLICY.md:
        - Name similarity: 50% weight
        - Email exact match: 50% weight

        Args:
            parent_id: Parent company partner_sk
            full_name: Full name
            email: Email address

        Returns:
            List of match candidates
        """
        normalized_name = Normalizer.normalize_string(full_name)

        # TODO: Query candidates WHERE parent_sk = :parent_id
        candidates_from_db = []

        results = []
        for candidate in candidates_from_db:
            candidate_name = Normalizer.normalize_string(candidate['name'])
            name_score = Levenshtein.jaro_winkler(normalized_name, candidate_name)

            # Email exact match
            email_score = 1.0 if (email and candidate.get('email') and email.lower() == candidate['email'].lower()) else 0.0

            combined = 0.5 * name_score + 0.5 * email_score

            results.append(MatchCandidate(
                record_id=candidate['partner_sk'],
                record_data=candidate,
                score=combined,
                match_logic=f"name:{name_score:.2f} email:{email_score:.2f}"
            ))

        results.sort(key=lambda c: c.score, reverse=True)
        return results

    def _fuzzy_match_lead(
        self,
        name: str,
        email_from: str,
        create_date: Optional[date]
    ) -> List[MatchCandidate]:
        """
        Fuzzy match lead.

        From MATCHING_POLICY.md:
        - Name similarity: 40%
        - Email exact: 40%
        - Date proximity: 20%

        Args:
            name: Lead name
            email_from: Email
            create_date: Creation date

        Returns:
            List of match candidates
        """
        normalized_name = Normalizer.normalize_string(name)

        # TODO: Query candidates from fact_lead
        candidates_from_db = []

        results = []
        for candidate in candidates_from_db:
            candidate_name = Normalizer.normalize_string(candidate['name'])
            name_score = Levenshtein.jaro_winkler(normalized_name, candidate_name)

            email_score = 1.0 if email_from.lower() == candidate.get('email_from', '').lower() else 0.0

            # Date proximity (within 7 days = 1.0, linear decay over 30 days)
            if create_date and candidate.get('create_date'):
                date_diff = abs((create_date - candidate['create_date']).days)
                date_score = max(0, 1.0 - (date_diff / 30.0))
            else:
                date_score = 0.0

            combined = 0.4 * name_score + 0.4 * email_score + 0.2 * date_score

            results.append(MatchCandidate(
                record_id=candidate['lead_sk'],
                record_data=candidate,
                score=combined,
                match_logic=f"name:{name_score:.2f} email:{email_score:.2f} date:{date_score:.2f}"
            ))

        results.sort(key=lambda c: c.score, reverse=True)
        return results
