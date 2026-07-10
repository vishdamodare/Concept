"""Backend tests for the Emergent Google Auth flow.

Covers:
- POST /api/auth/session (missing session_id -> 400, invalid -> 401)
- session_token accepted via Bearer header and via cookie
- expired session -> 401
- logout deletes the row from db.user_sessions and clears cookies
- upsert reuses existing user id when Google email matches an existing JWT user
- startup indexes exist on db.user_sessions (session_token unique + expires_at TTL)
- coexistence: existing JWT flow still works (regression sample)
"""
import os
import uuid
import subprocess
import json
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE}/api"

DB_NAME = "conceptforge_db"

LEARNER_EMAIL = "learner@conceptforge.app"
LEARNER_PASSWORD = "learner123"


# ------------------ helpers ------------------

def mongosh(js: str) -> str:
    """Run a mongosh eval statement and return stdout."""
    cmd = ["mongosh", "--quiet", "--eval", f"use('{DB_NAME}'); {js}"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"mongosh failed: {res.stderr}\n{res.stdout}"
    return res.stdout.strip()


def ensure_learner():
    """Register learner if not present (idempotent)."""
    r = requests.post(f"{API}/auth/login",
                      json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD}, timeout=10)
    if r.status_code == 200:
        return r.json()
    r = requests.post(f"{API}/auth/register",
                      json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD, "name": "Learner"}, timeout=10)
    assert r.status_code == 200, f"learner setup failed: {r.text}"
    return r.json()


def insert_fake_session(user_id: str, session_token: str, expires_delta_seconds: int = 7 * 24 * 3600):
    """Insert a fake session_token row directly via mongosh."""
    expiry_ms = int((datetime.now(timezone.utc) + timedelta(seconds=expires_delta_seconds)).timestamp() * 1000)
    js = (
        f"db.user_sessions.insertOne({{"
        f"user_id: '{user_id}', "
        f"session_token: '{session_token}', "
        f"expires_at: new Date({expiry_ms}), "
        f"created_at: new Date()"
        f"}}); print('inserted');"
    )
    out = mongosh(js)
    assert "inserted" in out


def insert_fake_user(email: str) -> str:
    """Insert a fresh Google-only user directly, return user_id."""
    uid = str(uuid.uuid4())
    js = (
        f"db.users.insertOne({{id: '{uid}', email: '{email}', name: 'Fake Google', "
        f"picture: 'https://example.com/pic.png', role: 'user', "
        f"auth_provider: 'google', created_at: new Date().toISOString()}}); print('ok');"
    )
    out = mongosh(js)
    assert "ok" in out
    return uid


def cleanup_session(session_token: str):
    mongosh(f"db.user_sessions.deleteMany({{session_token: '{session_token}'}}); print('cleaned');")


def cleanup_user_by_email(email: str):
    mongosh(f"db.user_sessions.deleteMany({{}}); db.users.deleteMany({{email: '{email}'}});")


# ------------------ Indexes ------------------

class TestIndexes:
    def test_user_sessions_indexes_exist(self):
        out = mongosh("printjson(db.user_sessions.getIndexes());")
        assert "session_token" in out
        assert "unique: true" in out or "unique:true" in out
        assert "expires_at" in out
        assert "expireAfterSeconds" in out


# ------------------ /api/auth/session ------------------

class TestExchangeSession:
    def test_missing_session_id_returns_400(self):
        r = requests.post(f"{API}/auth/session", json={}, timeout=10)
        assert r.status_code == 400, r.text
        data = r.json()
        assert "session_id" in (data.get("detail") or "").lower()

    def test_invalid_session_id_returns_401(self):
        # Any random string -> Emergent auth returns non-200 -> our endpoint 401
        r = requests.post(f"{API}/auth/session", json={},
                          headers={"X-Session-ID": f"bogus-{uuid.uuid4().hex}"},
                          timeout=20)
        # Emergent may occasionally return a 5xx if unreachable; we only accept 401
        assert r.status_code == 401, f"expected 401 for bogus session_id, got {r.status_code}: {r.text}"


# ------------------ Session token acceptance (Bearer + cookie) ------------------

class TestSessionTokenAcceptance:
    def setup_method(self):
        self.email = f"google_user_{uuid.uuid4().hex[:8]}@conceptforge.app"
        self.user_id = insert_fake_user(self.email)
        self.token = f"testsess_{uuid.uuid4().hex}"
        insert_fake_session(self.user_id, self.token)

    def teardown_method(self):
        cleanup_session(self.token)
        cleanup_user_by_email(self.email)

    def test_me_with_bearer_session_token(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == self.user_id
        assert data["email"] == self.email
        assert "password_hash" not in data
        # google users should have a picture field
        assert data.get("picture") == "https://example.com/pic.png"

    def test_me_with_cookie_session_token(self):
        cookies = {"session_token": self.token}
        r = requests.get(f"{API}/auth/me", cookies=cookies, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == self.user_id


class TestExpiredSession:
    def test_expired_session_token_returns_401(self):
        email = f"exp_user_{uuid.uuid4().hex[:8]}@conceptforge.app"
        user_id = insert_fake_user(email)
        token = f"expired_{uuid.uuid4().hex}"
        try:
            insert_fake_session(user_id, token, expires_delta_seconds=-3600)  # 1 hr in the past
            r = requests.get(f"{API}/auth/me", cookies={"session_token": token}, timeout=10)
            assert r.status_code == 401
            r2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            assert r2.status_code == 401
        finally:
            cleanup_session(token)
            cleanup_user_by_email(email)


# ------------------ Logout deletes session ------------------

class TestLogout:
    def test_logout_deletes_session_and_clears_cookie(self):
        email = f"lo_user_{uuid.uuid4().hex[:8]}@conceptforge.app"
        user_id = insert_fake_user(email)
        token = f"logout_{uuid.uuid4().hex}"
        insert_fake_session(user_id, token)
        try:
            # First confirm session works
            r = requests.get(f"{API}/auth/me", cookies={"session_token": token}, timeout=10)
            assert r.status_code == 200

            s = requests.Session()
            s.cookies.set("session_token", token,
                          domain=BASE.replace("https://", "").replace("http://", ""))
            r_out = s.post(f"{API}/auth/logout", timeout=10)
            assert r_out.status_code == 200
            # session row should be gone
            out = mongosh(f"print(db.user_sessions.countDocuments({{session_token: '{token}'}}));")
            assert out.strip().endswith("0"), f"expected 0 remaining sessions, mongosh out={out}"

            # Cookies should be cleared in response headers
            set_cookies = r_out.headers.get("set-cookie", "")
            assert "session_token=" in set_cookies
            assert "access_token=" in set_cookies
        finally:
            cleanup_session(token)
            cleanup_user_by_email(email)


# ------------------ Upsert reuses existing JWT user_id ------------------

class TestUserUpsertReuse:
    def test_existing_jwt_user_id_is_reused_when_google_session_created(self):
        # Ensure learner exists via JWT
        learner = ensure_learner()
        jwt_user_id = learner["id"]
        assert jwt_user_id

        # Simulate what /auth/session does *after* Emergent lookup: it upserts on
        # db.users by email. We can't call the endpoint (external), but we test
        # the invariant: if we insert a session bound to the existing user's id,
        # /auth/me returns that same id — confirming user linkage by id, not by
        # accidental duplicate user row.
        token = f"reuse_{uuid.uuid4().hex}"
        insert_fake_session(jwt_user_id, token)
        try:
            r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["id"] == jwt_user_id, "session must resolve to the SAME user_id as JWT flow"
            # Only one user row for learner email
            count_out = mongosh(f"print(db.users.countDocuments({{email: '{LEARNER_EMAIL}'}}));")
            assert count_out.strip().endswith("1"), f"expected exactly 1 learner user row, got: {count_out}"
        finally:
            cleanup_session(token)


# ------------------ Regression: existing JWT flow still works ------------------

class TestJwtCoexistence:
    def test_jwt_login_still_returns_token_and_me(self):
        ensure_learner()
        r = requests.post(f"{API}/auth/login",
                          json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD}, timeout=10)
        assert r.status_code == 200
        tok = r.json()["token"]
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        assert me.status_code == 200
        assert me.json()["email"] == LEARNER_EMAIL

    def test_jwt_and_session_bearer_both_supported(self):
        # JWT
        ensure_learner()
        tok_jwt = requests.post(f"{API}/auth/login",
                                json={"email": LEARNER_EMAIL,
                                      "password": LEARNER_PASSWORD}, timeout=10).json()["token"]
        # Session
        email = f"dual_{uuid.uuid4().hex[:8]}@conceptforge.app"
        uid = insert_fake_user(email)
        tok_sess = f"dual_{uuid.uuid4().hex}"
        insert_fake_session(uid, tok_sess)
        try:
            r1 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok_jwt}"}, timeout=10)
            r2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok_sess}"}, timeout=10)
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.json()["email"] == LEARNER_EMAIL
            assert r2.json()["email"] == email
        finally:
            cleanup_session(tok_sess)
            cleanup_user_by_email(email)
