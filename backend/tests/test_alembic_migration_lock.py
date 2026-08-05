from contextlib import contextmanager, nullcontext
import runpy
from unittest.mock import MagicMock, patch

import alembic.context


def _load_env_without_running_online_migrations():
    fake_config = MagicMock()
    fake_config.config_file_name = None
    fake_config.get_main_option.return_value = "sqlite+aiosqlite://"
    with patch.object(alembic.context, "config", fake_config, create=True), patch.object(
        alembic.context, "is_offline_mode", return_value=True
    ), patch.object(alembic.context, "configure"), patch.object(
        alembic.context, "begin_transaction", return_value=nullcontext()
    ), patch.object(alembic.context, "run_migrations"):
        return runpy.run_path("alembic/env.py")


def test_postgresql_lock_wraps_migration_plan_and_unlocks_on_failure(monkeypatch):
    env = _load_env_without_running_online_migrations()
    events = []
    connection = MagicMock()
    connection.dialect.name = "postgresql"
    connection.execute.side_effect = lambda statement: events.append(str(statement))

    @contextmanager
    def transaction():
        events.append("begin")
        try:
            yield
        finally:
            events.append("end")

    def fail_migrations():
        events.append("run_migrations")
        raise RuntimeError("migration failed")

    with patch.object(alembic.context, "configure", side_effect=lambda **_: events.append("configure")), patch.object(
        alembic.context, "begin_transaction", side_effect=transaction
    ), patch.object(alembic.context, "run_migrations", side_effect=fail_migrations):
        try:
            env["do_run_migrations"](connection)
        except RuntimeError:
            pass

    assert "pg_advisory_lock" in events[0]
    assert events.index("run_migrations") > events.index("configure")
    assert "pg_advisory_unlock" in events[-1]
