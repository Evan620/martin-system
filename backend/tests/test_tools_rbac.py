import pytest
from app.tools._rbac import (
    EDIT_ROLES, INVESTOR_ROLES, SECRETARIAT_ONLY,
    require_role, propose_action,
)
from app.models.models import UserRole  # only used for the enum


def test_edit_roles_membership():
    assert UserRole.ADMIN in EDIT_ROLES
    assert UserRole.SECRETARIAT_LEAD in EDIT_ROLES
    assert UserRole.TWG_FACILITATOR in EDIT_ROLES
    assert UserRole.TWG_MEMBER not in EDIT_ROLES


def test_require_role_passes_for_allowed():
    err = require_role(UserRole.ADMIN, EDIT_ROLES)
    assert err is None


def test_require_role_returns_forbidden_for_disallowed():
    err = require_role(UserRole.TWG_MEMBER, EDIT_ROLES)
    assert err == {
        "status": "forbidden",
        "reason": "Requires one of: ADMIN, SECRETARIAT_LEAD, TWG_FACILITATOR",
    }


def test_propose_action_shape():
    out = propose_action(
        action_type="advance_project_stage",
        summary="Advance \"X\" to SUMMIT_READY.",
        payload={"project_id": "abc", "target_stage": "SUMMIT_READY"},
        irreversible=False,
    )
    assert out["status"] == "confirmation_required"
    assert out["action_type"] == "advance_project_stage"
    assert out["summary"].startswith("Advance")
    assert out["payload"]["project_id"] == "abc"
    assert "action_id" in out and len(out["action_id"]) >= 8
    assert out["confirm_endpoint"] == "/api/v1/agents/execute"
    assert out["irreversible"] is False
