#!/usr/bin/env bash
# Repair a Postgres database whose alembic_version row points at a revision
# that no longer exists in alembic/versions/ (a "phantom marker").
#
# This is a one-time fix per database. After it runs, `alembic upgrade head`
# becomes a clean no-op on that DB and future deploys self-migrate normally.
#
# Usage (prod, from a laptop with Railway CLI):
#   railway run -s backend bash backend/scripts/repair_alembic_state.sh
#
# Usage (local):
#   cd backend && bash scripts/repair_alembic_state.sh
#
# Required env: DATABASE_URL (sqlalchemy or libpq style accepted).
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set." >&2
  exit 1
fi

cd "$(dirname "$0")/.."

# Diagnose. Exit 0 = healthy (skip repair). Exit 2 = phantom detected (do repair).
set +e
python - <<'PY'
import os, sys, re, pathlib
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
e = create_engine(url)

with e.connect() as c:
    rows = c.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
print(f"DB alembic_version: {rows}")

versions_dir = pathlib.Path("alembic/versions")
known = set()
for f in versions_dir.glob("*.py"):
    m = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", f.read_text(), re.M)
    if m:
        known.add(m.group(1))

phantom = [r for r in rows if r not in known]
if phantom:
    print(f"PHANTOM marker detected: {phantom}. Known revisions: {len(known)}.")
    sys.exit(2)
print(f"OK: alembic_version is at a real revision. Known revisions: {len(known)}. No repair needed.")
sys.exit(0)
PY
diag=$?
set -e

case "$diag" in
  0)
    echo "Healthy. Skipping stamp."
    ;;
  2)
    echo "Repairing: stamping DB to head with --purge."
    alembic stamp head --purge
    echo "--- verify ---"
    alembic current
    echo "--- alembic upgrade head should now be a clean no-op ---"
    alembic upgrade head
    ;;
  *)
    echo "Diagnostic step failed with code $diag." >&2
    exit "$diag"
    ;;
esac

echo "Done."
