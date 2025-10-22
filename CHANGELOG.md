# Changelog

## 2025-10-22 — 06:35 CST

- Confirmed the knowledge base-backed deterministic mapper is the active mapping path and ensured required Python deps (`networkx`) load within the project virtualenv.
- Removed the legacy `HeaderMatcher` implementation and all implicit fallbacks so mapping now relies solely on the deterministic mapper or hybrid matcher (`backend/app/services/mapping_service.py`).
- Updated supporting tooling/tests to target the hybrid matcher (`backend/test_new_matcher.py`, `backend/tests/matcher_validation/test_simple_matcher.py`).
- Refreshed documentation to reflect the streamlined mapping stack and legacy removal (`ARCHITECTURE.md`, `CLAUDE.md`, `IMPLEMENTATION_SUMMARY.md`, `MAPPING_SYSTEM_ARCHITECTURE.md`, `docs/architecture/ARCHITECTURE.yaml`).
