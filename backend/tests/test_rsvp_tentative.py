"""TENTATIVE ('Maybe') is a first-class RSVP state in both the model + schema enums."""
from app.models.models import RsvpStatus as ModelRsvp
from app.schemas.schemas import RsvpStatus as SchemaRsvp
from app.schemas.schemas import MeetingParticipantUpdate


def test_model_enum_has_tentative():
    assert ModelRsvp.TENTATIVE.value == "TENTATIVE"


def test_schema_enum_has_tentative():
    assert SchemaRsvp.TENTATIVE.value == "TENTATIVE"


def test_participant_update_accepts_tentative():
    upd = MeetingParticipantUpdate(rsvp_status="TENTATIVE")
    assert upd.rsvp_status == SchemaRsvp.TENTATIVE
