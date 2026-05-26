"""Application-wide constants.

Keep this file small and dependency-free. Anything imported by both
routes and services lives here so we avoid circular imports.
"""

# ---------------------------------------------------------------------------
# R5 — Incubation document checklist
# ---------------------------------------------------------------------------
# Canonical codes (uppercase) are the authoritative slot keys for the six-item
# Incubation document checklist. Aliases are case-insensitive legacy strings
# previously used in the Document.document_type column — they continue to
# satisfy the slot so we don't have to migrate existing rows.
INCUBATION_CHECKLIST_ITEMS: list[tuple[str, str]] = [
    ("FEASIBILITY", "Preliminary Feasibility Study"),
    ("LAND_RIGHTS", "Land Rights / Site Control"),
    ("GOV_SUPPORT", "Government Support Letter"),
    ("ENV_ASSESSMENT", "Environmental Pre-Assessment"),
    ("FINANCIAL_MODEL", "Financial Model"),
    ("CORE_TEAM", "Core Project Team Identified"),
]

DOC_TYPE_ALIASES: dict[str, set[str]] = {
    "FEASIBILITY": {"feasibility_study", "feasibility"},
    "LAND_RIGHTS": {"land_rights", "site_control"},
    "GOV_SUPPORT": {"government_letter", "noc", "gov_support"},
    "ENV_ASSESSMENT": {"esia_screening", "environmental_assessment", "env_assessment"},
    "FINANCIAL_MODEL": {"financial_model"},
    "CORE_TEAM": {"team", "org_chart", "core_team"},
}


def normalize_doc_type(value: str | None) -> str | None:
    """Lowercase + strip a document_type value for alias comparison."""
    if value is None:
        return None
    return value.strip().lower()


def canonical_code_for(document_type: str | None) -> str | None:
    """Return the canonical checklist code that a document_type satisfies,
    or None if it matches no slot. Case-insensitive."""
    if not document_type:
        return None
    normalized = document_type.strip().lower()
    for code, _ in INCUBATION_CHECKLIST_ITEMS:
        if normalized == code.lower():
            return code
        aliases = DOC_TYPE_ALIASES.get(code, set())
        if normalized in {a.lower() for a in aliases}:
            return code
    return None
