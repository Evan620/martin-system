import uuid

from app.models.models import UserRole


def test_expired_admin_binding_is_rejected_and_removed(monkeypatch):
    import app.tools._rbac as rbac

    now = [100.0]
    monkeypatch.setattr(rbac, "_monotonic", lambda: now[0])
    thread_id = f"expired-{uuid.uuid4()}"
    token = rbac.set_user_for_thread(
        thread_id, str(uuid.uuid4()), UserRole.ADMIN, ttl_seconds=5
    )

    now[0] = 106.0
    assert rbac.get_thread_user_context(thread_id, token) is None
    assert thread_id not in rbac._user_by_thread


def test_owner_checked_cleanup_cannot_remove_newer_rebinding():
    from app.tools._rbac import (
        clear_user_for_thread,
        get_thread_user_context,
        set_user_for_thread,
    )

    thread_id = f"rebind-{uuid.uuid4()}"
    old_user = str(uuid.uuid4())
    new_user = str(uuid.uuid4())
    old_token = set_user_for_thread(thread_id, old_user, UserRole.ADMIN)
    new_token = set_user_for_thread(thread_id, new_user, UserRole.TWG_MEMBER)

    assert clear_user_for_thread(thread_id, old_token) is False
    assert get_thread_user_context(thread_id, old_token) is None
    assert get_thread_user_context(thread_id, new_token) == (
        new_user,
        UserRole.TWG_MEMBER,
    )
    assert clear_user_for_thread(thread_id, new_token) is True
    assert get_thread_user_context(thread_id, new_token) is None


def test_thread_lookup_never_falls_back_to_stale_contextvar():
    from app.tools._rbac import get_user_for_thread, set_user_context

    set_user_context(str(uuid.uuid4()), UserRole.ADMIN)
    assert get_user_for_thread(f"unbound-{uuid.uuid4()}") is None


def test_thread_binding_map_remains_bounded(monkeypatch):
    import app.tools._rbac as rbac

    monkeypatch.setattr(rbac, "_MAX_THREADS", 3)
    with rbac._thread_user_lock:
        rbac._user_by_thread.clear()
    for index in range(5):
        rbac.set_user_for_thread(
            f"bounded-{index}", str(uuid.uuid4()), UserRole.TWG_MEMBER
        )

    assert len(rbac._user_by_thread) == 3


def test_repeated_conversation_binding_cleanup_does_not_clear_agent_history():
    from app.agents.agent_loop import AgentLoop
    from app.tools._rbac import clear_user_for_thread, set_user_for_thread

    thread_id = f"history-{uuid.uuid4()}"
    AgentLoop._history[thread_id] = [{"role": "user", "content": "remember me"}]
    first = set_user_for_thread(thread_id, str(uuid.uuid4()), UserRole.ADMIN)
    assert clear_user_for_thread(thread_id, first) is True
    second = set_user_for_thread(thread_id, str(uuid.uuid4()), UserRole.ADMIN)
    assert clear_user_for_thread(thread_id, second) is True

    assert AgentLoop._history[thread_id] == [
        {"role": "user", "content": "remember me"}
    ]
