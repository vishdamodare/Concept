"""Backend tests for /api/concepts/{id}/export endpoint (Iteration 5).

Uses learner@conceptforge.app which has existing ready concepts so we don't need
to wait ~110s for fresh generation. A second user is registered for cross-user
access control. A separate 'generating' status test reuses a fresh stub via the
test_a flow if needed; here we rely on the seeded library for the happy path.
"""
import os
import time
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE}/api"

LEARNER = {"email": "learner@conceptforge.app", "password": "learner123"}
RUN_ID = uuid.uuid4().hex[:8]
USER_B = {"email": f"test_exp_{RUN_ID}@conceptforge.app", "password": "secret123", "name": "Exp B"}


def H(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def learner_token():
    r = requests.post(f"{API}/auth/login", json=LEARNER, timeout=15)
    if r.status_code != 200:
        # Register if not present
        r_reg = requests.post(f"{API}/auth/register", json={
            "email": LEARNER["email"],
            "password": LEARNER["password"],
            "name": "Learner"
        }, timeout=15)
        assert r_reg.status_code == 200, f"Register failed: {r_reg.text}"
        # Login again
        r = requests.post(f"{API}/auth/login", json=LEARNER, timeout=15)
        assert r.status_code == 200, f"Login after register failed: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def user_b_token():
    r = requests.post(f"{API}/auth/register", json=USER_B, timeout=15)
    assert r.status_code == 200, f"register B failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def ready_concept(learner_token):
    """Pick the first ready concept from learner's library."""
    r = requests.get(f"{API}/concepts", headers=H(learner_token), timeout=15)
    assert r.status_code == 200
    items = r.json()
    ready = [c for c in items if c.get("status") in (None, "ready")]
    if not ready:
        import pymongo
        client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = client[os.environ.get("DB_NAME", "conceptforge")]
        user = db.users.find_one({"email": LEARNER["email"]})
        user_id = user["id"]
        dummy = {
            "id": f"dummy-{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "name": "Quicksort algorithm",
            "level": "beginner",
            "status": "ready",
            "stage": "done",
            "roadmap": {
                "summary": "Quicksort is an efficient sorting algorithm.",
                "prerequisites": ["Arrays", "Recursion"],
                "milestones": [
                    {
                        "title": "Introduction to Quicksort",
                        "description": "Understand the basic divide-and-conquer strategy.",
                        "topics": ["Divide and conquer", "Partitioning"],
                        "key_questions": ["What is partitioning?"],
                        "exercise": "Trace quicksort manually.",
                        "estimate": "1 hour"
                    }
                ],
                "video_queries": ["quicksort animation"],
                "search_queries": ["quicksort complexity"],
                "image_prompt": "schematic layout of quicksort partition step",
                "study_guide_outline": ["Intro", "Partition", "Complexity"]
            },
            "study_guide": "## Why this matters\nSorting is key.\n## Core ideas\nDivide and conquer.\n## How it actually works (step-by-step)\nChoose pivot.\n## Worked example\n[3, 1, 2] -> [1, 2, 3]\n## Intuition & mental models\nPartitioning books.\n## Common pitfalls and misconceptions\nBad pivot choices.\n## Going deeper (advanced angles)\nIn-place quicksort.\n## Practice questions\n1. What is worst case?\nAnswer: O(N^2) if sorted and bad pivot.\n2. Space complexity?\nAnswer: O(log N).\n3. Stable?\nAnswer: Not stable.\n4. Pivot choice?\nAnswer: Random is best.\n5. Average case?\nAnswer: O(N log N).\n6. When to use?\nAnswer: General sorting.",
            "videos": [
                {
                    "title": "Quicksort Algorithm",
                    "embed": "https://www.youtube.com/embed/vector_sort"
                }
            ],
            "resources": {
                "categories": [
                    {
                        "name": "Official documentation",
                        "items": [
                            {"title": "Python lists doc", "url": "https://docs.python.org", "description": "Docs on list operations", "kind": "docs"},
                            {"title": "C++ Sort doc", "url": "https://cppreference.com", "description": "Reference on std::sort", "kind": "docs"}
                        ]
                    }
                ]
            },
            "created_at": "2026-06-09T14:16:56.924612+00:00"
        }
        db.concepts.insert_one(dummy)
        r = requests.get(f"{API}/concepts", headers=H(learner_token), timeout=15)
        items = r.json()
        ready = [c for c in items if c.get("status") in (None, "ready")]
    return ready[0]


# ---------------- Happy path: Markdown ----------------
class TestExportMarkdown:
    def test_md_status_and_headers(self, learner_token, ready_concept):
        cid = ready_concept["id"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=md", headers=H(learner_token), timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        assert "text/markdown" in ctype.lower(), f"bad content-type: {ctype}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert ".md" in cd.lower(), f"missing .md in CD: {cd}"

    def test_md_body_structure(self, learner_token, ready_concept):
        cid = ready_concept["id"]
        name = ready_concept["name"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=md", headers=H(learner_token), timeout=30)
        assert r.status_code == 200
        body = r.text
        # H1 with concept name on first line
        first_line = body.split("\n", 1)[0]
        assert first_line.startswith("# "), f"first line not H1: {first_line!r}"
        assert name in first_line, f"concept name {name!r} not in H1: {first_line!r}"
        # Required sections
        lower = body.lower()
        assert "summary" in lower
        assert "roadmap" in lower
        assert "study guide" in lower
        assert "resources" in lower
        assert "videos" in lower
        # Roadmap milestones use checkbox emoji or markdown task list markers
        assert ("[ ]" in body) or ("[x]" in body) or ("☐" in body) or ("✅" in body) or ("⬜" in body), \
            "no checkbox markers found in roadmap"
        # Resources include markdown links
        assert "](http" in body, "no markdown links to http(s) found"


# ---------------- Happy path: PDF ----------------
class TestExportPdf:
    def test_pdf_status_and_bytes(self, learner_token, ready_concept):
        cid = ready_concept["id"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=pdf", headers=H(learner_token), timeout=120)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        assert "application/pdf" in ctype.lower(), f"bad content-type: {ctype}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower() and ".pdf" in cd.lower(), f"bad CD: {cd}"
        # Valid PDF: starts with %PDF- and is reasonably sized
        assert r.content[:5] == b"%PDF-", f"not a PDF: starts with {r.content[:8]!r}"
        assert len(r.content) > 10_000, f"PDF too small: {len(r.content)} bytes"


# ---------------- Error cases ----------------
class TestExportErrors:
    def test_invalid_format_400(self, learner_token, ready_concept):
        cid = ready_concept["id"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=xyz", headers=H(learner_token), timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"

    def test_cross_user_404(self, user_b_token, ready_concept):
        cid = ready_concept["id"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=md", headers=H(user_b_token), timeout=15)
        assert r.status_code == 404, f"expected 404 cross-user, got {r.status_code} {r.text[:200]}"

    def test_unauthenticated_401(self, ready_concept):
        cid = ready_concept["id"]
        r = requests.get(f"{API}/concepts/{cid}/export?format=md", timeout=15)
        assert r.status_code == 401

    def test_generating_status_409(self, learner_token):
        """Kick off async generate (returns immediately with status=generating),
        then attempt export immediately -> 409."""
        payload = {"name": f"ExportTest_{RUN_ID}", "level": "beginner"}
        r = requests.post(f"{API}/concepts/generate", json=payload, headers=H(learner_token), timeout=15)
        assert r.status_code == 200, f"generate failed: {r.status_code} {r.text[:200]}"
        init = r.json()
        assert init.get("status") == "generating"
        cid = init["id"]
        try:
            # Export immediately while still generating
            r2 = requests.get(f"{API}/concepts/{cid}/export?format=md", headers=H(learner_token), timeout=15)
            assert r2.status_code == 409, f"expected 409, got {r2.status_code} {r2.text[:200]}"
        finally:
            # best-effort cleanup: wait briefly then delete (works even if still generating per DELETE rules)
            try:
                # don't block test on completion; just delete after a small wait
                time.sleep(2)
                requests.delete(f"{API}/concepts/{cid}", headers=H(learner_token), timeout=15)
            except Exception:
                pass
