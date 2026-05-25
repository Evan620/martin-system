"""R8 coordinate scout — best-guess site coordinates from project metadata.

When a project lacks `site_lat`/`site_lon`, this service asks the LLM to
infer plausible GPS coordinates from the project's textual content (name,
description, lead country, sponsor, value chain). The result is returned
to the facilitator for confirmation BEFORE persisting — the caller decides
whether to save the suggestion.

The LLM has solid geographic knowledge of ECOWAS regions; for projects that
name a specific district, irrigation scheme, or industrial corridor it can
reach city-or-region-level accuracy, which is enough for the satellite
analysis to produce useful signals."""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Project
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are a geospatial analyst working for AfCEN (the ECOWAS Centre of Excellence for Investment). You are given a development project's textual metadata and asked to infer the most plausible GPS coordinates for its primary on-the-ground site.

Rules:
- Output JSON only. No prose, no markdown fencing.
- ECOWAS countries: Benin, Burkina Faso, Cape Verde, Côte d'Ivoire, Gambia, Ghana, Guinea, Guinea-Bissau, Liberia, Mali, Niger, Nigeria, Senegal, Sierra Leone, Togo.
- Prefer rural/agricultural coordinates over city centroids. If the project mentions a specific district, irrigation scheme, industrial corridor, or named site, pin near it.
- If multi-country, pick the dominant country's main site and note the ambiguity in `reasoning`.
- If the project is broad / national-scale with no specific site, pick the country's most relevant agricultural region for the project's commodity/value chain.
- Coordinates must fall on land (no ocean pins).
- `confidence` 0.0-1.0: 0.9+ when a specific site name is mentioned, 0.5-0.7 for region-level inference, <0.4 if only the country is known.

Output schema:
{
  "lat": <float>,
  "lon": <float>,
  "place_name": "<human-readable, e.g. 'Office du Niger rice belt near Ségou, Mali'>",
  "confidence": <0.0-1.0>,
  "reasoning": "<1-3 sentences explaining the placement>"
}"""


class CoordinateScoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def scout(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Infer coordinates for a project. Does NOT persist — returns the
        suggestion for the caller to confirm or reject."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            return {"error": "project_not_found"}

        prompt = _build_prompt(project)
        llm = get_llm_service()

        try:
            # Note: max_tokens must cover reasoning-model thinking tokens too.
            # On gpt-5.5 / o-series, the response budget eats both the
            # internal chain-of-thought and the visible output. 400 wasn't
            # enough; the model silently returned an empty string.
            raw = llm.chat(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.warning("LLM scout failed for project %s: %s", project_id, e)
            return {"error": "llm_failed", "message": str(e)}

        parsed = _parse_llm_json(raw)
        if parsed is None:
            return {"error": "llm_parse_failed", "raw": raw[:400] if isinstance(raw, str) else str(raw)[:400]}

        # Validation
        try:
            lat = float(parsed["lat"])
            lon = float(parsed["lon"])
        except (KeyError, TypeError, ValueError):
            return {"error": "invalid_coords", "raw": raw}
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return {"error": "coords_out_of_range", "lat": lat, "lon": lon}

        return {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "place_name": parsed.get("place_name", ""),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", ""),
            "project_id": str(project_id),
        }


def _build_prompt(project: Project) -> str:
    """Compact project summary for the LLM. Skips empty fields."""
    parts = [f"Project name: {project.name}"]
    if project.lead_country:
        parts.append(f"Lead country: {project.lead_country}")
    if project.pillar:
        parts.append(f"Pillar: {project.pillar}")
    if project.subsector:
        parts.append(f"Subsector: {project.subsector}")
    if project.project_sponsor:
        parts.append(f"Sponsor: {project.project_sponsor}")
    if project.value_chain_stages:
        parts.append(f"Value chain stages: {', '.join(project.value_chain_stages)}")
    if project.description:
        # First 800 chars of description — usually enough for location signal
        desc = project.description[:800]
        parts.append(f"Description: {desc}")
    parts.append("\nReturn JSON with lat, lon, place_name, confidence, reasoning.")
    return "\n".join(parts)


def _parse_llm_json(raw: Any) -> Optional[Dict[str, Any]]:
    """LLMs occasionally return JSON wrapped in prose or markdown fences.
    Strip and parse defensively."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    # Strip ``` and language tags
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON object in the text
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def get_coordinate_scout_service(db: AsyncSession) -> CoordinateScoutService:
    return CoordinateScoutService(db)
