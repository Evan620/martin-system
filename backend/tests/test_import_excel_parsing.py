"""
Regression tests for the deal-pipeline Excel importer.

Built from two REAL submitted sheets:
  - twg_template_agriculture.xlsx  — the official TWG template, Agriculture tab
  - moe_energy_ministry_sheet.xlsx — a hand-modified ministry sheet (MoE/Energy)
    where "Project Title" was split into a row-1 banner and the real header row
    has a blank first cell. This is the sheet that caused every Energy project
    to land in Digital Transformation.

The importer must:
  1. Detect the real header row even when a "Project Title" banner sits above it.
  2. Map the project name to the first column when the header's name cell is blank.
  3. Map "Energy"/"Agribusiness" sectors to the correct pillar.
  4. Fall back to the importing TWG's pillar (NOT Digital) when sector is missing.
  5. Skip instruction/section/description rows.
"""
import os
import openpyxl
import pytest

from app.api.routes.pipeline import parse_pipeline_workbook, _match_pillar
from app.models.models import TWGPillar

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "import_sheets")
MOE = os.path.join(FIXTURES, "moe_energy_ministry_sheet.xlsx")
AG = os.path.join(FIXTURES, "twg_template_agriculture.xlsx")


def _load(path):
    return openpyxl.load_workbook(path, data_only=True)


# --- _match_pillar: must NOT silently default to Digital -------------------

def test_match_pillar_known_sectors():
    assert _match_pillar("Energy") == TWGPillar.energy_infrastructure
    assert _match_pillar("Agribusiness") == TWGPillar.agriculture_food_systems
    assert _match_pillar("Strategic Minerals") == TWGPillar.critical_minerals_industrialization


def test_match_pillar_unknown_returns_none():
    # Unknown / empty must return None so the caller can fall back to the
    # importing TWG's pillar — NOT silently become Digital.
    assert _match_pillar("") is None
    assert _match_pillar("   ") is None
    assert _match_pillar("Something Unrecognized") is None


# --- MoE ministry sheet: the regression that started this ------------------

def test_moe_energy_sheet_does_not_become_digital():
    wb = _load(MOE)
    projects, skipped, errors = parse_pipeline_workbook(
        wb, fallback_pillar=TWGPillar.energy_infrastructure.value
    )
    assert projects, "should import at least the real Energy projects"
    # The whole point: NOTHING should land in Digital from an Energy import.
    digital = [p for p in projects if p["pillar"] == TWGPillar.digital_economy_transformation.value]
    assert not digital, f"{len(digital)} projects wrongly mapped to Digital: {[p['name'] for p in digital][:5]}"
    # All should be Energy (sector cell says Energy; fallback is Energy too).
    assert all(p["pillar"] == TWGPillar.energy_infrastructure.value for p in projects)
    # Known real project must be present with its real name.
    names = [p["name"] for p in projects]
    assert any("Mission 300" in n for n in names), names[:5]


def test_moe_sheet_skips_instruction_and_section_rows():
    wb = _load(MOE)
    projects, skipped, errors = parse_pipeline_workbook(
        wb, fallback_pillar=TWGPillar.energy_infrastructure.value
    )
    names_lower = [p["name"].lower() for p in projects]
    for junk in (
        "complete one row per project",
        "section a",
        "basic project information",
        "full name of the project",
    ):
        assert not any(junk in n for n in names_lower), f"junk row imported: {junk}"


# --- Official Agriculture template: must keep working ----------------------

def test_agriculture_template_maps_to_agriculture():
    wb = _load(AG)
    projects, skipped, errors = parse_pipeline_workbook(
        wb, fallback_pillar=TWGPillar.agriculture_food_systems.value
    )
    assert projects
    agri = [p for p in projects if p["pillar"] == TWGPillar.agriculture_food_systems.value]
    # The vast majority must be Agriculture (the sheet's Sector column says
    # "Agribusiness"). At least one row in this real sheet is mislabeled in the
    # source (Sector typed as "Digital Transformation"); the parser correctly
    # respects the explicit sector rather than silently overriding it.
    assert len(agri) >= len(projects) - 1, [(p["name"], p["pillar"]) for p in projects]
    names = [p["name"] for p in projects]
    assert any("Bobo-Dioulasso" in n for n in names), names[:5]
    # description row must be skipped
    assert not any("full name of the project" in n.lower() for n in names)


def test_explicit_sector_is_respected_over_twg_fallback():
    # A row whose Sector explicitly names a recognized pillar wins over the
    # import TWG's fallback (so genuinely mixed sheets aren't flattened).
    wb = _load(AG)
    projects, _, _ = parse_pipeline_workbook(
        wb, fallback_pillar=TWGPillar.agriculture_food_systems.value
    )
    mislabeled = [p for p in projects if "resilience accelerator" in p["name"].lower()]
    assert mislabeled, "expected the known mislabeled row to be present"
    assert mislabeled[0]["pillar"] == TWGPillar.digital_economy_transformation.value
