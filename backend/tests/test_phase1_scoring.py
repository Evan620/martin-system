"""
Phase 1 scoring tests — 9 WAIIS criteria seed + scoring functions.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.project_pipeline_service import ProjectPipelineService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_ensure_default_criteria_seeds_9_criteria(mock_db):
    """_ensure_default_criteria must seed exactly 9 named criteria."""
    # Simulate empty criteria table
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = empty_result

    service = ProjectPipelineService(mock_db)
    await service._ensure_default_criteria()

    added_names = [call.args[0].criterion_name for call in mock_db.add.call_args_list]
    assert len(added_names) == 9, f"Expected 9 criteria, got {len(added_names)}: {added_names}"
    assert "Climate Impact" in added_names
    assert "Social Impact" in added_names
    assert "Economic Impact" in added_names
    assert "ECOWAS Integration" in added_names
    assert "Additionality" not in added_names


@pytest.mark.asyncio
async def test_ensure_default_criteria_skips_if_already_seeded(mock_db):
    """Must not re-seed if all 9 criteria already exist."""
    NINE_NAMES = {
        "Readiness", "Scale of Impact", "Country & Political Enablement",
        "Bankability", "Climate Impact", "Social Impact",
        "Economic Impact", "ECOWAS Integration", "Scalability/Replicability"
    }
    existing = [MagicMock(criterion_name=n) for n in NINE_NAMES]
    result = MagicMock()
    result.scalars.return_value.all.return_value = existing
    mock_db.execute.return_value = result

    service = ProjectPipelineService(mock_db)
    mock_db.add.reset_mock()
    await service._ensure_default_criteria()

    mock_db.add.assert_not_called()


def make_project(**kwargs):
    """Build a minimal mock Project with sensible defaults."""
    p = MagicMock()
    p.investment_size = kwargs.get('investment_size', 10_000_000)
    p.is_cross_border = kwargs.get('is_cross_border', False)
    p.climate_impact = kwargs.get('climate_impact', None)
    p.ghg_avoided_target = kwargs.get('ghg_avoided_target', None)
    p.esg_compliance = kwargs.get('esg_compliance', None)
    p.jobs_construction = kwargs.get('jobs_construction', None)
    p.jobs_om = kwargs.get('jobs_om', None)
    p.smallholder_farmers_reached = kwargs.get('smallholder_farmers_reached', None)
    p.women_employment_pct = kwargs.get('women_employment_pct', None)
    p.youth_employment_pct = kwargs.get('youth_employment_pct', None)
    p.macroeconomic_roi = kwargs.get('macroeconomic_roi', None)
    p.revenue_model = kwargs.get('revenue_model', None)
    p.financing_structure = kwargs.get('financing_structure', None)
    p.permits_licences = kwargs.get('permits_licences', None)
    p.land_status = kwargs.get('land_status', None)
    p.technical_studies = kwargs.get('technical_studies', None)
    p.project_sponsor = kwargs.get('project_sponsor', None)
    p.lead_country = kwargs.get('lead_country', 'Ghana')
    return p


def test_climate_impact_score_with_ghg_and_keyword():
    service = ProjectPipelineService.__new__(ProjectPipelineService)
    agg = {"has_feasibility_study": False, "has_esia": False, "has_financial_model": True,
           "has_government_support": False, "has_permits": False, "has_site_control": False,
           "cross_border_impact": False, "esg_compliant": False, "irr_percentage": None, "npv_value": None}
    p = make_project(ghg_avoided_target="50,000 tCO2e", climate_impact="solar irrigation renewable energy project")
    scores = service._compute_waiis_sub_scores(p, agg)
    assert scores["Climate Impact"] >= 60, f"Expected >=60, got {scores['Climate Impact']}"


def test_climate_impact_score_zero_without_data():
    service = ProjectPipelineService.__new__(ProjectPipelineService)
    agg = {"has_feasibility_study": False, "has_esia": False, "has_financial_model": False,
           "has_government_support": False, "has_permits": False, "has_site_control": False,
           "cross_border_impact": False, "esg_compliant": False, "irr_percentage": None, "npv_value": None}
    p = make_project()
    scores = service._compute_waiis_sub_scores(p, agg)
    assert scores["Climate Impact"] == 0.0


def test_social_impact_score_with_gender_youth():
    service = ProjectPipelineService.__new__(ProjectPipelineService)
    agg = {"has_feasibility_study": False, "has_esia": False, "has_financial_model": False,
           "has_government_support": False, "has_permits": False, "has_site_control": False,
           "cross_border_impact": False, "esg_compliant": False, "irr_percentage": None, "npv_value": None}
    p = make_project(
        jobs_construction="150 jobs", jobs_om="80 jobs",
        smallholder_farmers_reached="600 smallholders",
        women_employment_pct=35.0, youth_employment_pct=28.0
    )
    scores = service._compute_waiis_sub_scores(p, agg)
    assert scores["Social Impact"] == 100.0


def test_ecowas_score_cross_border_ecowas_country():
    service = ProjectPipelineService.__new__(ProjectPipelineService)
    agg = {"has_feasibility_study": False, "has_esia": False, "has_financial_model": False,
           "has_government_support": False, "has_permits": False, "has_site_control": False,
           "cross_border_impact": False, "esg_compliant": False, "irr_percentage": None, "npv_value": None}
    p = make_project(is_cross_border=True, lead_country="Ghana")
    scores = service._compute_waiis_sub_scores(p, agg)
    assert scores["ECOWAS Integration"] >= 60, f"Expected >=60, got {scores['ECOWAS Integration']}"


def test_ecowas_score_zero_non_ecowas():
    service = ProjectPipelineService.__new__(ProjectPipelineService)
    agg = {"has_feasibility_study": False, "has_esia": False, "has_financial_model": False,
           "has_government_support": False, "has_permits": False, "has_site_control": False,
           "cross_border_impact": False, "esg_compliant": False, "irr_percentage": None, "npv_value": None}
    p = make_project(is_cross_border=False, lead_country="Kenya")  # Kenya not in ECOWAS
    scores = service._compute_waiis_sub_scores(p, agg)
    assert scores["ECOWAS Integration"] == 20.0  # only 20 pts for lead_country non-ECOWAS
