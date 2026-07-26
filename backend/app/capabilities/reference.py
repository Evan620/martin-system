"""Backward-compatible imports for the moved reference declarations."""

from app.capabilities.declarations.reference import (
    ListTWGMembersInput,
    registry_create_action_item,
    registry_list_twg_members,
)

__all__ = [
    "ListTWGMembersInput",
    "registry_create_action_item",
    "registry_list_twg_members",
]
