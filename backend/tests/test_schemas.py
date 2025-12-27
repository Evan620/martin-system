import pytest
from app.schemas.schemas import TWGCreate, UserCreate, UserRole, TWGPillar

def test_user_schema_validation():
    """Test UserCreate schema validation."""
    # Valid data
    user_in = UserCreate(
        full_name="Alice Smith",
        email="alice@example.com",
        role=UserRole.TWG_MEMBER,
        password="securepassword"
    )
    assert user_in.full_name == "Alice Smith"
    
    # Invalid email
    with pytest.raises(ValueError):
        UserCreate(
            full_name="Alice Smith",
            email="invalid-email",
            role=UserRole.TWG_MEMBER
        )

def test_twg_schema_validation():
    """Test TWGCreate schema validation."""
    twg_in = TWGCreate(
        name="Digital Economy TWG",
        pillar=TWGPillar.DIGITAL
    )
    assert twg_in.name == "Digital Economy TWG"
    assert twg_in.pillar == TWGPillar.DIGITAL
