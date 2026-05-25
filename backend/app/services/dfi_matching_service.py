from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    BlendedFinancePackage, BlendedFinanceTranche,
    DFIInstrumentType, DFIMatchStatus, DFIWindow, Project, ProjectDFIMatch,
)
from app.services.llm_service import llm_service
from loguru import logger


def _default_fallback_tranches(total_ask: float, top_matches) -> List[Dict[str, Any]]:
    """When LLM is unavailable, return a generic 3-tranche stack so the UI doesn't
    show empty data. The amounts split 10/60/30 (grant/concessional/commercial).
    Labels are explicitly marked as placeholders."""
    if not total_ask or total_ask <= 0:
        return []
    grant_amt = round(total_ask * 0.10)
    concessional_amt = round(total_ask * 0.60)
    commercial_amt = total_ask - grant_amt - concessional_amt  # absorbs rounding
    tranches = []
    if top_matches:
        # Use the highest-fit eligible window as a hint for the concessional layer
        for i, m in enumerate(top_matches[:1]):
            tranches.append({
                "label": f"[placeholder] {m.dfi_window.institution} concessional layer",
                "dfi_window_name": m.dfi_window.name,
                "instrument_type": "CONCESSIONAL_LOAN",
                "amount_usd": concessional_amt,
                "tenor_years": None,
                "coupon_pct": None,
                "seniority": 2,
                "is_first_loss": False,
                "notes": "Placeholder — AI advisor unavailable, default 60% concessional layer.",
            })
    else:
        tranches.append({
            "label": "[placeholder] concessional layer",
            "dfi_window_name": None,
            "instrument_type": "CONCESSIONAL_LOAN",
            "amount_usd": concessional_amt,
            "tenor_years": None,
            "coupon_pct": None,
            "seniority": 2,
            "is_first_loss": False,
            "notes": "Placeholder — AI advisor unavailable.",
        })
    tranches.append({
        "label": "[placeholder] commercial debt",
        "dfi_window_name": None,
        "instrument_type": "BLENDED",
        "amount_usd": commercial_amt,
        "tenor_years": None,
        "coupon_pct": None,
        "seniority": 1,
        "is_first_loss": False,
        "notes": "Placeholder — AI advisor unavailable.",
    })
    tranches.append({
        "label": "[placeholder] first-loss grant",
        "dfi_window_name": None,
        "instrument_type": "GRANT",
        "amount_usd": grant_amt,
        "tenor_years": None,
        "coupon_pct": None,
        "seniority": 3,
        "is_first_loss": True,
        "notes": "Placeholder first-loss tranche — AI advisor unavailable.",
    })
    return tranches


# Map ProjectStatus values to stage labels used in DFI window eligible_stages
_STAGE_MAP: Dict[str, str] = {
    "INCUBATION": "Concept",
    "DRAFT": "Concept",
    "PIPELINE": "Concept",
    "UNDER_REVIEW": "Feasibility",
    "SUMMIT_READY": "Feasibility",
    "DEAL_ROOM_FEATURED": "Development",
    "IN_NEGOTIATION": "Development",
    "COMMITTED": "Construction",
    "NEEDS_REVISION": "Feasibility",
    "DECLINED": "Concept",
}

# Map pillar names to normalized sector labels
_SECTOR_NORMALISE: Dict[str, str] = {
    "ENERGY": "Energy",
    "AGRICULTURE": "Agriculture",
    "DIGITAL": "Digital",
    "MINERALS": "Minerals",
    "STRATEGIC MINERALS": "Minerals",
    "RESOURCE_MOBILIZATION": "Cross-Sector",
    "CROSS-SECTOR": "Cross-Sector",
    "CROSS_SECTOR": "Cross-Sector",
    "INDUSTRIALISATION": "Cross-Sector",
}


class DFIMatchingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_dfi_windows(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Score project against all active DFI windows and upsert matches >= 40."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        windows_result = await self.db.execute(
            select(DFIWindow).where(DFIWindow.is_active.is_(True))
        )
        windows = windows_result.scalars().all()

        new_matches = 0
        updated_matches = 0

        ineligible_count = 0
        for window in windows:
            eligible, inelig_reason = self._check_eligibility(project, window)
            score, rationale = self._score_project_window(project, window)
            # Create a match row even if ineligible (with score=0 and a clear reason),
            # so reviewers can see WHY a window does not apply to this project rather
            # than the window silently disappearing from the list.
            if not eligible:
                outcome = await self._upsert_match(
                    project, window, 0, f"INELIGIBLE: {inelig_reason}",
                    eligible=False, ineligibility_reason=inelig_reason,
                )
                if outcome == "created":
                    ineligible_count += 1
                continue
            if score >= 40:
                outcome = await self._upsert_match(
                    project, window, score, rationale,
                    eligible=True, ineligibility_reason=None,
                )
                if outcome == "created":
                    new_matches += 1
                elif outcome == "updated":
                    updated_matches += 1

        await self.db.commit()
        return {
            "project_id": str(project_id),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "ineligible_windows": ineligible_count,
            "windows_scanned": len(windows),
        }

    def _check_eligibility(self, project: Project, window: DFIWindow) -> Tuple[bool, Optional[str]]:
        """R7 — Evaluate `window.concessional_eligibility_rules` against the project.

        Returns (eligible: bool, reason: str | None). When eligible is False, the
        reason is a human-readable string suitable to show in the UI.

        Rules without a corresponding project field are treated as "pass" (we don't
        penalise a project for missing data we never asked for).
        """
        rules = window.concessional_eligibility_rules or {}
        if not rules:
            return True, None

        inv = float(project.investment_size or 0)
        pillar = (project.pillar or "").lower()
        country = (project.lead_country or "").lower()

        if (max_size := rules.get("max_project_size_usd")) is not None and inv > float(max_size):
            return False, f"Project size ${inv/1e6:.1f}M exceeds window max ${float(max_size)/1e6:.1f}M"
        if (min_size := rules.get("min_project_size_usd")) is not None and inv < float(min_size):
            return False, f"Project size ${inv/1e6:.1f}M below window min ${float(min_size)/1e6:.1f}M"

        if required_pillars := rules.get("required_pillar"):
            if not any(p.lower() in pillar for p in required_pillars):
                return False, f"Project pillar '{project.pillar}' not in window's required list ({', '.join(required_pillars)})"

        if allowed := rules.get("allowed_lead_countries"):
            if country and not any(c.lower() in country or country in c.lower() for c in allowed):
                return False, f"Lead country '{project.lead_country}' outside window's allowed list"

        if excluded := rules.get("excluded_lead_countries"):
            if country and any(c.lower() in country or country in c.lower() for c in excluded):
                return False, f"Lead country '{project.lead_country}' is in window's exclusion list"

        if required_vc := rules.get("required_value_chain"):
            stages = set(project.value_chain_stages or [])
            if not stages.intersection(required_vc):
                return False, f"Project value chain ({', '.join(stages) or 'none'}) doesn't include any required: {', '.join(required_vc)}"

        if rules.get("requires_gender_intentional") and not project.gender_intentional:
            return False, "Window requires gender-intentional design; project not flagged"

        if rules.get("requires_climate_target") and not (project.ghg_avoided_target and str(project.ghg_avoided_target).strip()):
            return False, "Window requires a quantified climate impact target; project has none set"

        if rules.get("requires_cross_border") and not project.is_cross_border:
            return False, "Window requires cross-border integration; project is single-country"

        return True, None

    def _score_project_window(self, project: Project, window: DFIWindow) -> Tuple[int, str]:
        """Rule-based scoring of a project against one DFI window. Returns (score 0-100, rationale)."""
        score = 0
        reasons: List[str] = []

        # +35: sector overlap
        project_sectors: set = set()
        if project.pillar:
            normalised = _SECTOR_NORMALISE.get(project.pillar.upper(), project.pillar.title())
            project_sectors.add(normalised)
        for stage in (project.value_chain_stages or []):
            normalised = _SECTOR_NORMALISE.get(stage.upper(), stage.title())
            project_sectors.add(normalised)

        window_sectors = set(window.sectors or [])
        if "ALL" in window_sectors or (project_sectors & window_sectors):
            score += 35
            overlap = project_sectors & window_sectors
            reasons.append(f"Sector match: {', '.join(overlap) if overlap else 'cross-sector window'}")

        # +25: geography coverage
        window_geos = {g.upper() for g in (window.geographies or [])}
        geo_match = (
            (project.lead_country and project.lead_country.upper() in window_geos)
            or "ECOWAS" in window_geos
            or "WEST AFRICA" in window_geos
            or "AFRICA" in window_geos
            or "GLOBAL" in window_geos
        )
        if geo_match:
            score += 25
            reasons.append(f"Geographic coverage includes {project.lead_country or 'ECOWAS region'}")

        # +20: investment size within range
        if project.investment_size:
            size_usd = float(project.investment_size)
            min_ok = window.min_size_usd is None or size_usd >= window.min_size_usd
            max_ok = window.max_size_usd is None or size_usd <= window.max_size_usd
            if min_ok and max_ok:
                score += 20
                reasons.append(f"Investment size (${size_usd:,.0f}) fits window range")

        # +10: development stage eligible
        project_stage = _STAGE_MAP.get(
            (project.status.value if hasattr(project.status, 'value') else str(project.status)).upper(),
            ""
        )
        eligible = window.eligible_stages or []
        if project_stage and project_stage in eligible:
            score += 10
            reasons.append(f"Stage eligible: {project_stage}")

        # +5: gender bonus
        if window.gender_focus and project.gender_intentional:
            score += 5
            reasons.append("Gender-intentional project matches gender-focused window")

        # +5: climate bonus
        if window.climate_focus and project.ghg_avoided_target:
            score += 5
            reasons.append("Climate impact target aligns with climate-focused window")

        rationale = " · ".join(reasons) if reasons else "No strong match signals"
        return min(score, 100), rationale

    async def _upsert_match(
        self,
        project: Project,
        window: DFIWindow,
        score: int,
        rationale: str,
        *,
        eligible: bool = True,
        ineligibility_reason: Optional[str] = None,
    ) -> str:
        result = await self.db.execute(
            select(ProjectDFIMatch).where(
                ProjectDFIMatch.project_id == project.id,
                ProjectDFIMatch.dfi_window_id == window.id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            changed = (
                existing.fit_score != score
                or existing.eligible != eligible
                or existing.ineligibility_reason != ineligibility_reason
            )
            if changed:
                existing.fit_score = score
                existing.fit_rationale = rationale
                existing.eligible = eligible
                existing.ineligibility_reason = ineligibility_reason
                return "updated"
            return "skipped"
        self.db.add(ProjectDFIMatch(
            project_id=project.id,
            dfi_window_id=window.id,
            fit_score=score,
            status=DFIMatchStatus.IDENTIFIED,
            fit_rationale=rationale,
            eligible=eligible,
            ineligibility_reason=ineligibility_reason,
        ))
        return "created"

    async def get_matches_for_project(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ProjectDFIMatch)
            .where(ProjectDFIMatch.project_id == project_id)
            .options(selectinload(ProjectDFIMatch.dfi_window))
            .order_by(ProjectDFIMatch.fit_score.desc())
        )
        matches = result.scalars().all()
        return [
            {
                "match_id": str(m.id),
                "dfi_window": m.dfi_window,
                "fit_score": m.fit_score,
                "fit_rationale": m.fit_rationale,
                "status": m.status.value,
                "notes": m.notes,
            }
            for m in matches
        ]

    async def update_match_status(
        self,
        match_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ProjectDFIMatch).where(ProjectDFIMatch.id == match_id)
        )
        match = result.scalar_one_or_none()
        if not match:
            return {"error": "Match not found"}
        match.status = DFIMatchStatus(new_status.upper())
        if notes is not None:
            match.notes = notes
        await self.db.commit()
        return {"match_id": str(match.id), "status": match.status.value}

    async def generate_financing_memo(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Generate a structured blended finance memo for a project using LLM."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        # Fetch top ELIGIBLE DFI matches only — never recommend tranches from
        # windows the project doesn't qualify for under R7 eligibility rules.
        matches_result = await self.db.execute(
            select(ProjectDFIMatch)
            .where(
                ProjectDFIMatch.project_id == project_id,
                ProjectDFIMatch.eligible.is_(True),
            )
            .options(selectinload(ProjectDFIMatch.dfi_window))
            .order_by(ProjectDFIMatch.fit_score.desc())
            .limit(5)
        )
        top_matches = matches_result.scalars().all()
        window_list = "\n".join(
            f"- {m.dfi_window.name} ({m.dfi_window.institution}) — "
            f"fit score {m.fit_score}/100, instrument: {m.dfi_window.instrument_type.value}, "
            f"window range: ${m.dfi_window.min_size_usd or 0:,.0f} – "
            f"${m.dfi_window.max_size_usd or float('inf'):,.0f}"
            for m in top_matches
        ) if top_matches else "No ELIGIBLE DFI windows matched — run matching engine first or check eligibility filters."

        total_ask = float(project.investment_size or 0)
        prompt = f"""
Project: {project.name}
Sector / Pillar: {project.pillar}
Country: {project.lead_country or 'West Africa'}
Investment Size: ${total_ask:,.0f} USD
Funding Secured: ${float(project.funding_secured_usd or 0):,.0f} USD
Development Stage: {project.status}
Gender-Intentional: {project.gender_intentional or False}
Climate Impact Target: {project.ghg_avoided_target or 'Not specified'}
Value Chain Stages: {', '.join(project.value_chain_stages or []) or 'Not specified'}

Top Matching (ELIGIBLE) DFI Windows:
{window_list}

Produce a blended finance structuring memo in exactly this JSON shape (no markdown,
raw JSON). The `tranches` array models the actual capital stack — typically 2 to 4
layers — where seniority=1 is most senior (commercial debt repaid first) and higher
numbers are more junior (concessional / grant / first-loss equity absorb losses first
to protect commercial capital). Tranche amounts must sum to the total Investment Size
above. Use REAL DFI window names from the list above for `dfi_window_name`.

{{
  "recommended_structure": "<1 sentence describing the capital stack>",
  "grant_component_pct": <0-100 integer>,
  "concessional_component_pct": <0-100 integer>,
  "commercial_component_pct": <0-100 integer>,
  "tranches": [
    {{
      "label": "<e.g. 'AfDB ADPP senior concessional loan'>",
      "dfi_window_name": "<exact window name from the list above, or null for commercial banks>",
      "instrument_type": "<one of: GRANT | CONCESSIONAL_LOAN | EQUITY | BLENDED>",
      "amount_usd": <integer USD>,
      "tenor_years": <integer or null>,
      "coupon_pct": <number or null>,
      "seniority": <1=most senior, higher=more junior>,
      "is_first_loss": <true|false>,
      "notes": "<short rationale for this layer>"
    }}
  ],
  "priority_windows": ["<window name>", "<window name>", "<window name>"],
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "full_memo": "<3-4 paragraph financing rationale>"
}}
"""
        system_prompt = (
            "You are a blended finance structuring expert for the ECOWAS Investment Summit. "
            "Produce concise, accurate financing memos grounded in the project data provided. "
            "The three percentage components must sum to 100. The tranche amounts must sum "
            "to the total investment size. Use real DFI window names from the supplied list — "
            "never invent fictional facilities. Respond with raw JSON only."
        )

        source = "llm"
        error_class: Optional[str] = None
        try:
            raw = llm_service.chat(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4000,  # gpt-5.5 reasoning model consumes thinking tokens; tranches JSON needs ~800 of visible output — buffer the rest for reasoning
            )
            import json
            import re
            # Robust JSON extraction — strip markdown fences AND any surrounding prose
            s = (raw or "").strip()
            # Strip code fences
            if s.startswith("```"):
                s = s.lstrip("`")
                if s.lower().startswith("json"):
                    s = s[4:]
                s = s.strip()
                if s.endswith("```"):
                    s = s[:-3].strip()
            # Extract the first balanced JSON object if there's prose around it
            m = re.search(r"\{[\s\S]*\}", s)
            if m:
                s = m.group(0)
            memo = json.loads(s)
        except Exception as e:
            # AI unavailable — surface honestly to caller instead of pretending the
            # hardcoded default is a real recommendation. UI distinguishes via `source`.
            source = "default_fallback"
            error_class = type(e).__name__
            logger.warning(
                f"Financing memo LLM call failed ({error_class}); returning default_fallback for project {project_id}"
            )
            memo = {
                "recommended_structure": "AI advisor unavailable — default 60% concessional / 30% commercial / 10% grant shown as placeholder only",
                "grant_component_pct": 10,
                "concessional_component_pct": 60,
                "commercial_component_pct": 30,
                "tranches": _default_fallback_tranches(total_ask, top_matches),
                "priority_windows": [m.dfi_window.name for m in top_matches[:3]] if top_matches else [],
                "key_risks": [
                    "AI structuring advisor unavailable — this capital stack is a default placeholder, not a recommendation",
                    "Review with a finance specialist before sharing with project owner or investor",
                ],
                "next_steps": [
                    "Retry memo generation in a few minutes",
                    "If problem persists, structure manually using the top-matched DFI windows",
                ],
                "full_memo": (
                    "⚠ The AI structuring advisor was temporarily unavailable when this memo was requested. "
                    "The capital-stack breakdown shown is a static default (60/30/10) — not a recommendation grounded "
                    "in this project's specifics. Please retry, or have a finance specialist review the top-matched "
                    "DFI windows directly and structure the package manually."
                ),
            }

        # Persist as BlendedFinancePackage + tranches so it survives across page loads.
        await self._persist_package(project_id, total_ask, memo, source, error_class, top_matches)

        return {
            "project_id": str(project_id),
            "project_name": project.name,
            "source": source,
            "error_class": error_class,
            **memo,
        }

    async def _persist_package(
        self,
        project_id: uuid.UUID,
        total_ask: float,
        memo: Dict[str, Any],
        source: str,
        error_class: Optional[str],
        top_matches: List[ProjectDFIMatch],
    ) -> None:
        """Persist the memo as a BlendedFinancePackage + tranche rows. Idempotent —
        every call creates a new package (so history is preserved) and marks
        prior packages for this project as inactive.

        Bad tranche data from the LLM (unknown window names, non-numeric amounts)
        is filtered rather than raising — better to persist a partial package than
        lose the memo entirely.
        """
        # Mark older packages inactive
        old_pkgs = (await self.db.execute(
            select(BlendedFinancePackage).where(
                BlendedFinancePackage.project_id == project_id,
                BlendedFinancePackage.is_active.is_(True),
            )
        )).scalars().all()
        for pkg in old_pkgs:
            pkg.is_active = False

        # Build new package
        package = BlendedFinancePackage(
            project_id=project_id,
            name="AI-generated package" if source == "llm" else "Default fallback package",
            rationale=memo.get("recommended_structure"),
            total_amount_usd=total_ask,
            source=source,
            error_class=error_class,
            is_active=True,
        )
        self.db.add(package)
        await self.db.flush()  # so package.id is available

        # Map window name → window for tranche.dfi_window_id linkage
        windows_by_name = {m.dfi_window.name: m.dfi_window for m in top_matches if m.dfi_window}

        for t in memo.get("tranches") or []:
            try:
                amount = float(t.get("amount_usd") or 0)
                if amount <= 0:
                    continue
                instr_raw = (t.get("instrument_type") or "BLENDED").upper().strip()
                try:
                    instr = DFIInstrumentType(instr_raw)
                except ValueError:
                    instr = DFIInstrumentType.BLENDED
                window_name = t.get("dfi_window_name")
                window = windows_by_name.get(window_name) if window_name else None
                self.db.add(BlendedFinanceTranche(
                    package_id=package.id,
                    dfi_window_id=window.id if window else None,
                    label=str(t.get("label") or "Tranche")[:255],
                    instrument_type=instr,
                    amount_usd=amount,
                    tenor_years=int(t["tenor_years"]) if t.get("tenor_years") not in (None, "") else None,
                    coupon_pct=float(t["coupon_pct"]) if t.get("coupon_pct") not in (None, "") else None,
                    seniority=int(t.get("seniority") or 1),
                    is_first_loss=bool(t.get("is_first_loss") or False),
                    notes=t.get("notes"),
                ))
            except (TypeError, ValueError) as e:
                logger.warning(f"Skipping malformed tranche in memo: {e} | data: {t}")

        await self.db.commit()


def get_dfi_matching_service(db: AsyncSession) -> DFIMatchingService:
    return DFIMatchingService(db)
