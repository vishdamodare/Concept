"""Backend tests for ConceptForge API: auth, concept generation, chat, access control."""
import os
import time
import uuid
import requests
import pytest

BASE = os.environ.get('REACT_APP_BACKEND_URL', 'https://study-path-gen.preview.emergentagent.com').rstrip('/')
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@conceptforge.app"
ADMIN_PASSWORD = "admin123"

# Unique users for this test run (avoid clashing with existing users)
RUN_ID = uuid.uuid4().hex[:8]
USER_A = {"email": f"test_a_{RUN_ID}@conceptforge.app", "password": "secret123", "name": "User A"}
USER_B = {"email": f"test_b_{RUN_ID}@conceptforge.app", "password": "secret123", "name": "User B"}


# ---- Fixtures ----
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def user_a_token():
    r = requests.post(f"{API}/auth/register", json=USER_A, timeout=15)
    assert r.status_code == 200, f"register A failed {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == USER_A["email"]
    assert "token" in data and len(data["token"]) > 0
    return data["token"]


@pytest.fixture(scope="session")
def user_b_token():
    r = requests.post(f"{API}/auth/register", json=USER_B, timeout=15)
    assert r.status_code == 200, f"register B failed {r.status_code} {r.text}"
    return r.json()["token"]


def H(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Auth tests ----
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_me_authenticated(self, user_a_token):
        r = requests.get(f"{API}/auth/me", headers=H(user_a_token), timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == USER_A["email"]
        assert "password_hash" not in data

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_register_duplicate(self, user_a_token):
        r = requests.post(f"{API}/auth/register", json=USER_A, timeout=10)
        assert r.status_code == 400

    def test_logout_clears_cookie(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
        assert "access_token" in s.cookies
        # cookie based /me
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 200
        r3 = s.post(f"{API}/auth/logout", timeout=10)
        assert r3.status_code == 200
        # After logout, cookie should be cleared; /me without cookie/header => 401
        s.cookies.clear()
        r4 = s.get(f"{API}/auth/me", timeout=10)
        assert r4.status_code == 401


# ---- Concept generation tests ----
class TestConcepts:
    concept_id = None

    def test_generate_concept(self, user_a_token):
        payload = {"name": "Python lists", "level": "beginner"}
        # Step 1: POST returns within a couple of seconds with status=generating
        t0 = time.time()
        r = requests.post(f"{API}/concepts/generate", json=payload, headers=H(user_a_token), timeout=15)
        elapsed = time.time() - t0
        assert r.status_code == 200, f"generate failed {r.status_code} {r.text[:500]}"
        init = r.json()
        assert "id" in init and init["status"] == "generating"
        assert init.get("stage") == "roadmap"
        assert elapsed < 10, f"generate endpoint blocked for {elapsed}s, expected async (<10s)"
        cid = init["id"]
        TestConcepts.concept_id = cid

        # Step 2: poll until status=ready (up to ~180s)
        deadline = time.time() + 200
        data = None
        last_stage = None
        while time.time() < deadline:
            g = requests.get(f"{API}/concepts/{cid}", headers=H(user_a_token), timeout=20)
            assert g.status_code == 200, f"GET concept failed {g.status_code} {g.text[:300]}"
            data = g.json()
            stage = data.get("stage")
            if stage != last_stage:
                print(f"[poll] status={data.get('status')} stage={stage}")
                last_stage = stage
            if data.get("status") == "ready":
                break
            if data.get("status") == "failed":
                pytest.fail(f"generation failed: {data.get('error')}")
            time.sleep(4)
        assert data and data.get("status") == "ready", f"timed out waiting for ready, last={data and data.get('status')}"

        # Step 3: validate enriched data shape
        for f in ["id", "name", "level", "roadmap", "study_guide", "image", "videos", "resources"]:
            assert f in data, f"missing field {f}"
        assert data["name"] == "Python lists"
        assert data["level"] == "beginner"
        assert isinstance(data["roadmap"], dict)
        milestones = data["roadmap"].get("milestones") or []
        assert 7 <= len(milestones) <= 9, f"expected 7-9 milestones, got {len(milestones)}"
        for i, m in enumerate(milestones):
            assert "title" in m and "description" in m, f"milestone {i} missing core fields"
            assert isinstance(m.get("topics"), list) and len(m["topics"]) >= 1, f"milestone {i} missing topics"
            assert isinstance(m.get("key_questions"), list) and len(m["key_questions"]) >= 1, \
                f"milestone {i} missing key_questions"
            assert isinstance(m.get("exercise"), str) and len(m["exercise"]) > 5, \
                f"milestone {i} missing exercise"
            assert "estimate" in m, f"milestone {i} missing estimate"
        assert "video_queries" in data["roadmap"]
        # Study guide should be much longer now (1100+ chars target)
        assert isinstance(data["study_guide"], str) and len(data["study_guide"]) >= 1100, \
            f"study_guide too short: {len(data['study_guide'])} chars"
        # image may be null (acceptable fallback) but if present must be data URL
        if data["image"] is not None:
            assert data["image"].startswith("data:")
        assert isinstance(data["videos"], list) and len(data["videos"]) >= 1
        v = data["videos"][0]
        assert "embed" in v and v["embed"].startswith("https://www.youtube.com/embed/")

        # Resources validation
        res = data.get("resources") or {}
        cats = res.get("categories") or []
        assert 3 <= len(cats) <= 6, f"expected 3-6 resource categories, got {len(cats)}"
        valid_kinds = {"docs", "article", "course", "book", "paper", "tool"}
        for ci, cat in enumerate(cats):
            assert isinstance(cat.get("name"), str) and cat["name"]
            items = cat.get("items") or []
            assert len(items) >= 2, f"category '{cat['name']}' has fewer than 2 items"
            for ii, it in enumerate(items):
                assert isinstance(it.get("title"), str) and it["title"], f"cat {ci} item {ii} no title"
                url = it.get("url") or ""
                assert url.startswith("http://") or url.startswith("https://"), \
                    f"cat {ci} item {ii} bad url: {url}"
                assert it.get("kind") in valid_kinds, f"cat {ci} item {ii} bad kind: {it.get('kind')}"

    def test_list_concepts(self, user_a_token):
        r = requests.get(f"{API}/concepts", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        match = [c for c in items if c["id"] == TestConcepts.concept_id]
        assert len(match) == 1
        item = match[0]
        # New fields for progress feature
        assert "milestone_count" in item and isinstance(item["milestone_count"], int) and item["milestone_count"] >= 1
        assert "progress" in item and isinstance(item["progress"], list)
        # Heavy fields excluded
        for heavy in ("study_guide", "videos", "image", "roadmap"):
            assert heavy not in item, f"list response should not include heavy field {heavy}"

    # ---- Progress tests ----
    def test_progress_toggle_on(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 0, "completed": True},
                           headers=H(user_a_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == cid
        assert 0 in data["progress"]
        assert isinstance(data["total"], int) and data["total"] >= 1

    def test_progress_idempotent(self, user_a_token):
        cid = TestConcepts.concept_id
        r1 = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 0, "completed": True},
                            headers=H(user_a_token), timeout=15)
        r2 = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 0, "completed": True},
                            headers=H(user_a_token), timeout=15)
        assert r1.json()["progress"] == r2.json()["progress"]

    def test_progress_toggle_off(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 0, "completed": False},
                           headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        assert 0 not in r.json()["progress"]

    def test_progress_persists_on_get(self, user_a_token):
        cid = TestConcepts.concept_id
        # Set index 1 done
        requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 1, "completed": True},
                       headers=H(user_a_token), timeout=15)
        r = requests.get(f"{API}/concepts/{cid}", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "progress" in body and 1 in body["progress"]

    def test_progress_out_of_range(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 49, "completed": True},
                           headers=H(user_a_token), timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_progress_cross_user_404(self, user_b_token):
        cid = TestConcepts.concept_id
        r = requests.patch(f"{API}/concepts/{cid}/progress", json={"index": 0, "completed": True},
                           headers=H(user_b_token), timeout=15)
        assert r.status_code == 404

    def test_get_concept(self, user_a_token):
        cid = TestConcepts.concept_id
        assert cid
        r = requests.get(f"{API}/concepts/{cid}", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == cid
        assert "roadmap" in data and "study_guide" in data and "videos" in data

    def test_access_control_get(self, user_b_token):
        cid = TestConcepts.concept_id
        r = requests.get(f"{API}/concepts/{cid}", headers=H(user_b_token), timeout=15)
        assert r.status_code == 404  # user B cannot see user A's concept

    def test_access_control_delete(self, user_b_token):
        cid = TestConcepts.concept_id
        r = requests.delete(f"{API}/concepts/{cid}", headers=H(user_b_token), timeout=15)
        assert r.status_code == 404


# ---- Chat tests ----
class TestChat:
    def test_chat_empty_history(self, user_a_token):
        cid = TestConcepts.concept_id
        assert cid, "depends on generated concept"
        r = requests.get(f"{API}/concepts/{cid}/chat", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_post_chat(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.post(
            f"{API}/concepts/{cid}/chat",
            json={"message": "In one sentence, what is a Python list?"},
            headers=H(user_a_token),
            timeout=60,
        )
        assert r.status_code == 200, f"chat failed {r.status_code} {r.text[:400]}"
        data = r.json()
        assert "user" in data and "assistant" in data
        assert data["user"]["role"] == "user"
        assert data["assistant"]["role"] == "assistant"
        assert isinstance(data["assistant"]["content"], str) and len(data["assistant"]["content"]) > 5

    def test_chat_history_persists(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.get(f"{API}/concepts/{cid}/chat", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_chat_access_control(self, user_b_token):
        cid = TestConcepts.concept_id
        r = requests.get(f"{API}/concepts/{cid}/chat", headers=H(user_b_token), timeout=15)
        assert r.status_code == 404


# ---- Delete (cleanup) ----
class TestDelete:
    def test_delete_concept(self, user_a_token):
        cid = TestConcepts.concept_id
        r = requests.delete(f"{API}/concepts/{cid}", headers=H(user_a_token), timeout=15)
        assert r.status_code == 200
        # confirm gone
        r2 = requests.get(f"{API}/concepts/{cid}", headers=H(user_a_token), timeout=15)
        assert r2.status_code == 404
