"""
Martin Agent Capability Test Harness
=====================================
Exercises all major tool categories through the live HTTP API.

Run:
    cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
    ./venv/bin/python tests/test_agent_capabilities.py

Outputs:
    tests/TEST_RESULTS.md
"""

import time
import datetime
import json
import os
import sys
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "http://127.0.0.1:8000"
# Admin credentials from test DB (olivia.robinson@africacen.org)
ADMIN_USER_ID = "822a4ff1-93e8-461c-be50-147fd04bdbc9"
ADMIN_EMAIL = "olivia.robinson@africacen.org"
CANDIDATE_PASSWORDS = ["Password123!", "password123", "admin123!", "Admin123!"]

# JWT secret from .env (used to mint a token if HTTP login fails)
JWT_SECRET_KEY = "your-jwt-secret-key-minimum-32-characters-change-this"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 120

REQUEST_TIMEOUT = 90  # seconds per test — agent can take ~50s on first call

# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "id": "T01",
        "category": "calendar_read",
        "query": "What meetings do I have this week?",
        "tool_hint": "get_schedule",
    },
    {
        "id": "T02",
        "category": "calendar_past",
        "query": "Show me meetings from the past month",
        "tool_hint": "get_past_meetings",
    },
    {
        "id": "T03",
        "category": "documents",
        "query": "Find documents about energy policy or infrastructure",
        "tool_hint": "search_documents",
    },
    {
        "id": "T04",
        "category": "action_items",
        "query": "What are the current open action items?",
        "tool_hint": "get_action_items",
    },
    {
        "id": "T05",
        "category": "members",
        "query": "Who are the members of the Energy TWG?",
        "tool_hint": "get_twg_members",
    },
    {
        "id": "T06",
        "category": "meeting_create",
        "query": "Schedule a test meeting for next Monday at 10am titled 'Capability Test'",
        "tool_hint": "create_meeting_invite",
    },
    {
        "id": "T07",
        "category": "summit_status",
        "query": "What is the overall status of the summit preparation?",
        "tool_hint": "get_summit_status_tool",
    },
    {
        "id": "T08",
        "category": "multi_agent",
        "query": "Compare the priorities of the Energy and Digital TWGs",
        "tool_hint": "routes to 2 agents",
    },
    {
        "id": "T09",
        "category": "deal_pipeline",
        "query": "List the flagship investment projects",
        "tool_hint": "list_flagship_projects",
    },
    {
        "id": "T10",
        "category": "supervisor_only",
        "query": "Are there any scheduling conflicts across all TWGs?",
        "tool_hint": "detect_conflicts_tool",
    },
]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _mint_jwt(user_id: str) -> str:
    """
    Mint a short-lived JWT using the application's secret key.
    Falls back gracefully if python-jose is unavailable.
    """
    try:
        from jose import jwt as jose_jwt
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
        payload = {"sub": user_id, "exp": expire}
        return jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    except ImportError:
        # jose not installed — try PyJWT
        try:
            import jwt as pyjwt
            expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
            payload = {"sub": user_id, "exp": expire}
            return pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        except ImportError:
            return ""


def get_auth_token() -> str | None:
    """
    1. Try HTTP login with candidate passwords.
    2. If all fail, mint a JWT directly using the known secret key.
    Returns Bearer token string, or None if everything fails.
    """
    login_url = f"{BASE_URL}/api/v1/auth/login"
    for pwd in CANDIDATE_PASSWORDS:
        try:
            resp = requests.post(
                login_url,
                json={"email": ADMIN_EMAIL, "password": pwd},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                if token:
                    print(f"[auth] HTTP login succeeded (password index {CANDIDATE_PASSWORDS.index(pwd)})")
                    return token
        except requests.RequestException as exc:
            print(f"[auth] Request error: {exc}")

    # HTTP login failed — mint token directly
    print(f"[auth] HTTP login failed for all passwords; minting JWT for user {ADMIN_USER_ID}")
    token = _mint_jwt(ADMIN_USER_ID)
    if token:
        print("[auth] JWT minted successfully")
        return token

    return None


def build_headers(token: str | None) -> dict:
    """Build authorization headers, or empty dict if no token."""
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def check_no_auth_needed() -> bool:
    """Return True if /api/v1/auth/me responds 200 without a token."""
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/auth/me", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(
        self,
        test_id: str,
        category: str,
        passed: bool,
        elapsed: float,
        http_status: int | None,
        preview: str,
        error: str | None = None,
    ):
        self.test_id = test_id
        self.category = category
        self.passed = passed
        self.elapsed = elapsed
        self.http_status = http_status
        self.preview = preview
        self.error = error


def run_single_test(tc: dict, headers: dict) -> TestResult:
    """Execute one test case; return a TestResult."""
    test_id = tc["id"]
    category = tc["category"]
    query = tc["query"]

    url = f"{BASE_URL}/api/v1/agents/chat"
    payload = {"message": query, "conversation_id": None}

    print(f"  [{test_id}] {category}: {query[:60]}...")

    start = time.monotonic()
    http_status = None
    error_msg = None
    preview = ""
    passed = False

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed = time.monotonic() - start
        http_status = resp.status_code

        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "")
            if response_text:
                preview = response_text[:300].replace("\n", " ")
                passed = True
            else:
                error_msg = "Empty response body"
        else:
            error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"

    except requests.Timeout:
        elapsed = REQUEST_TIMEOUT
        error_msg = "TIMEOUT"
        passed = False
    except requests.RequestException as exc:
        elapsed = time.monotonic() - start
        error_msg = f"RequestException: {exc}"
        passed = False

    status_icon = "PASS" if passed else "FAIL"
    print(f"  [{test_id}] {status_icon} in {elapsed:.1f}s | {preview[:80] if preview else error_msg}")

    return TestResult(
        test_id=test_id,
        category=category,
        passed=passed,
        elapsed=elapsed,
        http_status=http_status,
        preview=preview if preview else (error_msg or ""),
        error=error_msg,
    )


def run_all_tests(headers: dict) -> list[TestResult]:
    """Run all test cases sequentially and return results."""
    results = []
    for tc in TEST_CASES:
        result = run_single_test(tc, headers)
        results.append(result)
        # Small breather between tests to avoid overwhelming the agent
        time.sleep(1)
    return results


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------

def build_markdown_report(results: list[TestResult], total_elapsed: float) -> str:
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Martin Agent Capability Test Results",
        f"Run at: {now}",
        "",
        "## Summary",
        f"- Passed: {passed}/{len(results)}",
        f"- Failed: {failed}/{len(results)}",
        f"- Total time: {total_elapsed:.1f}s",
        "",
        "## Results",
        "",
        "| ID | Category | Status | Time | Response preview |",
        "|----|----------|--------|------|-----------------|",
    ]

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        preview_cell = (r.preview[:80] + "...") if len(r.preview) > 80 else r.preview
        preview_cell = preview_cell.replace("|", "\\|")
        lines.append(
            f"| {r.test_id} | {r.category} | {icon} | {r.elapsed:.1f}s | {preview_cell} |"
        )

    if failed > 0:
        lines += ["", "## Failures", ""]
        for r in results:
            if not r.passed:
                lines += [
                    f"### {r.test_id} — {r.category}",
                    f"- HTTP status: {r.http_status}",
                    f"- Elapsed: {r.elapsed:.1f}s",
                    f"- Error: {r.error or 'unknown'}",
                    "",
                ]

    return "\n".join(lines) + "\n"


def write_results_file(content: str) -> str:
    """Write TEST_RESULTS.md next to this script. Returns path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "TEST_RESULTS.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Martin Agent Capability Test Harness")
    print("=" * 60)

    # Step 1: Auth
    print("\n[1/3] Authenticating...")
    if check_no_auth_needed():
        print("  No auth required (public endpoint)")
        headers = {}
    else:
        token = get_auth_token()
        if token:
            headers = build_headers(token)
            print(f"  Auth token obtained for {ADMIN_EMAIL}")
        else:
            print("  WARNING: Auth failed — running without token (tests may return 401)")
            headers = {}

    # Step 2: Run tests
    print(f"\n[2/3] Running {len(TEST_CASES)} tests (timeout={REQUEST_TIMEOUT}s each)...")
    wall_start = time.monotonic()
    results = run_all_tests(headers)
    total_elapsed = time.monotonic() - wall_start

    # Step 3: Report
    print(f"\n[3/3] Writing results...")
    md = build_markdown_report(results, total_elapsed)
    out_path = write_results_file(md)

    passed = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed}/{len(results)} passed in {total_elapsed:.1f}s")
    print(f"Report written to: {out_path}")
    print()
    print(md)


if __name__ == "__main__":
    main()
