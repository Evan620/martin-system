"""
Deal Room readiness continuum.

Every live project is placed on an inclusive continuum, from Boardroom
(investment-ready) through to Incubation (earliest stage). No project is
excluded for being early — the pipeline is built for the long term, with
early-stage opportunities kept and nurtured toward readiness.

Aligns with the WAIIS-2026 Deal Rooms ToR (Boardroom / Deal Room tracks plus
preparation referrals) and extends it into a continuous pipeline to 2030.

The tier is stored on `Project.deal_room_priority` (rank, 1 = most ready) and
`Project.investment_stage_label` (human label), and is recomputed whenever a
project is scored or changes status.
"""
from typing import Optional, Tuple

# rank -> (label, definition)
DEAL_ROOM_TIERS = {
    1: ("Boardroom",
        "Investment-ready: feasibility complete, sponsor and capital structure "
        "defined, creditworthy off-taker; signing-capable (term sheet / close)."),
    2: ("Deal Room",
        "Strong fundamentals but needs structuring, documentation or due "
        "diligence; matchmaking and a defined preparation pathway."),
    3: ("Preparation",
        "Viable but below the Deal Room bar; referred to preparation facilities "
        "(e.g. NEPAD-IPPF, SEFA, IRENA ETAF, UNIDO COMFAR)."),
    4: ("Early-stage",
        "Early but in the pipeline; concept or feasibility still forming. "
        "Nurtured toward readiness — not excluded."),
    5: ("Incubation",
        "Earliest ideas, SMEs and start-ups; long-term incubation lane."),
}

# Workflow statuses that imply investment-readiness (Boardroom).
_READY_STATUSES = {
    "IMPLEMENTED", "COMMITTED", "IN_NEGOTIATION", "DEAL_ROOM_FEATURED", "SUMMIT_READY",
}


def classify_deal_room_tier(status, afcen_score: Optional[float]) -> Tuple[Optional[int], Optional[str]]:
    """
    Place a project on the Deal Room continuum.

    Driven primarily by workflow status, lifted by the AfCEN score where one is
    present. Returns ``(rank, label)``; ``(None, None)`` for DECLINED projects,
    which sit outside the continuum.
    """
    s = status.value if hasattr(status, "value") else (str(status) if status else "")
    s = s.upper()
    sc = float(afcen_score) if afcen_score is not None else None

    if s == "DECLINED":
        return None, None

    if s in _READY_STATUSES or (sc is not None and sc >= 70):
        rank = 1
    elif s == "UNDER_REVIEW" or (sc is not None and 55 <= sc < 70):
        rank = 2
    elif s in ("PIPELINE", "NEEDS_REVISION") or (sc is not None and 40 <= sc < 55):
        rank = 3
    elif s == "INCUBATION":
        rank = 5
    else:  # DRAFT or anything unrecognised — keep it in the pipeline as early-stage
        rank = 4

    return rank, DEAL_ROOM_TIERS[rank][0]
