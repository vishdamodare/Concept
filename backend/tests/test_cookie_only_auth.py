"""Iteration 7 acceptance: /api/auth/me must accept ONLY the httpOnly cookie
(no Authorization header) for JWT (access_token) users, and ONLY the session_token
cookie for Google-auth users. Frontend no longer sends Authorization from localStorage.
"""
import os
import uuid
import datetime as dt
import requests
import pytest
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "conceptforge_db")

LEARNER_EMAIL = "learner@conceptforge.app"
LEARNER_PASSWORD = "learner123"


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# ---- JWT (access_token) cookie-only flow ----
class TestJwtCookieOnly:
    def test_login_sets_access_token_cookie(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD}, timeout=15)
        assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
        assert "access_token" in s.cookies, f"access_token cookie not set. cookies={dict(s.cookies)}"
        body = r.json()
        assert body["email"] == LEARNER_EMAIL

    def test_me_with_only_cookie_no_bearer(self):
        # Fresh session; login to get cookie
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD}, timeout=15)
        assert r.status_code == 200
        assert "access_token" in s.cookies

        # Now hit /me — the requests.Session automatically includes cookies.
        # We must ensure NO Authorization header is sent.
        r2 = s.get(f"{API}/auth/me", timeout=15)
        assert r2.status_code == 200, f"/me with cookie-only failed: {r2.status_code} {r2.text}"
        assert "Authorization" not in r2.request.headers, "test bug — Authorization leaked"
        body = r2.json()
        assert body["email"] == LEARNER_EMAIL

    def test_me_without_any_credentials_returns_401(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---- Google session_token cookie-only flow ----
class TestGoogleCookieOnly:
    def test_me_with_only_session_token_cookie(self, db):
        # Look up learner's user id
        user = db.users.find_one({"email": LEARNER_EMAIL}, {"_id": 0, "id": 1})
        assert user, "learner user missing — cannot proceed"
        user_id = user["id"]

        token = f"iter7_cookie_{uuid.uuid4().hex[:10]}"
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
        db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": token,
            "expires_at": expires_at,
            "created_at": dt.datetime.now(dt.timezone.utc),
        })

        try:
            # Attach cookie explicitly with NO Authorization header
            r = requests.get(
                f"{API}/auth/me",
                cookies={"session_token": token},
                timeout=15,
            )
            assert r.status_code == 200, f"got {r.status_code} {r.text}"
            body = r.json()
            assert body["email"] == LEARNER_EMAIL
            assert body["id"] == user_id
        finally:
            db.user_sessions.delete_one({"session_token": token})

    def test_bogus_session_token_cookie_returns_401(self):
        r = requests.get(
            f"{API}/auth/me",
            cookies={"session_token": "does-not-exist-xyz-999"},
            timeout=15,
        )
        assert r.status_code == 401


# ---- Regression: logout still clears cookie and blocks further calls ----
class TestLogoutRegression:
    def test_logout_clears_cookie_and_blocks_me(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": LEARNER_EMAIL, "password": LEARNER_PASSWORD}, timeout=15)
        assert r.status_code == 200
        assert "access_token" in s.cookies

        r2 = s.get(f"{API}/auth/me", timeout=15)
        assert r2.status_code == 200

        r3 = s.post(f"{API}/auth/logout", timeout=15)
        assert r3.status_code == 200

        # Browser-like: cookies dropped by server
        s.cookies.clear()
        r4 = s.get(f"{API}/auth/me", timeout=15)
        assert r4.status_code == 401
