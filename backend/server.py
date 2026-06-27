from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import logging
import asyncio
import base64
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated
import certifi

import bcrypt
import jwt
import markdown as md_lib
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Body
from fastapi.responses import PlainTextResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from llm.chat import LlmChat, UserMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("conceptforge")

# Keep strong references to running background tasks to prevent garbage collection mid-execution
active_tasks = set()

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
if 'MONGO_URL' not in os.environ:
    log.warning("MONGO_URL not set – using default localhost. Set this env var for production!")

# Use certifi CA bundle for SSL – fixes TLS handshake errors on Python 3.14 / Render
if 'mongodb+srv' in mongo_url or 'tls=true' in mongo_url.lower() or 'ssl=true' in mongo_url.lower():
    client = AsyncIOMotorClient(mongo_url, tlsCAFile=certifi.where())
else:
    client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'conceptforge')]

environment = os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or "development"
gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if gemini_key:
    if os.getenv("GEMINI_API_KEY"):
        log.info("Using GEMINI_API_KEY environment variable")
    else:
        log.info("Using GOOGLE_API_KEY environment variable")
else:
    if environment == "production":
        raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY in production!")
    else:
        log.warning("No Gemini/Google API key configured. LLM features will fail when used.")

log.info("===================================")
log.info("LLM Provider: Gemini")
log.info(f"Model: {os.getenv('LLM_MODEL', 'gemini/gemini-2.5-flash')}")
log.info(f"Environment: {environment}")
log.info("===================================")

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-me-in-production')
if 'JWT_SECRET' not in os.environ:
    log.warning("JWT_SECRET not set – using insecure default. Set this env var for production!")

JWT_ALG = 'HS256'

app = FastAPI(title="ConceptForge API")

@app.get("/health")
async def health():
    db_status = "connected"
    try:
        await db.command("ping")
    except Exception as e:
        db_status = f"disconnected ({str(e)})"
    return {
        "status": "ok",
        "database": db_status,
        "llm": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    }

api = APIRouter(prefix="/api")

# ----------------------------- Auth helpers --------------------------

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "email": email, "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token", value=token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * 7, path="/",
    )

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----------------------------- Models --------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GenerateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    level: str = Field(pattern="^(beginner|intermediate|advanced)$")

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class ProgressIn(BaseModel):
    index: int = Field(ge=0, le=49)
    completed: bool

# --- Consolidated Pydantic Schemas for Structured LLM Outputs ---
class MilestoneSchema(BaseModel):
    title: str
    description: str
    topics: List[str]
    key_questions: List[str]
    exercise: str
    estimate: str

class RoadmapSchema(BaseModel):
    summary: str
    prerequisites: List[str]
    milestones: List[MilestoneSchema]
    video_queries: List[str]
    search_queries: List[str]
    image_prompt: str
    study_guide_outline: List[str]

class ResourceItemSchema(BaseModel):
    title: str
    url: str
    description: str
    kind: str

class ResourceCategorySchema(BaseModel):
    name: str
    items: List[ResourceItemSchema]

class ResourcesSchema(BaseModel):
    categories: List[ResourceCategorySchema]

class ConceptResponseSchema(BaseModel):
    roadmap: RoadmapSchema
    study_guide: str
    resources: ResourcesSchema

CONSOLIDATED_CONCEPT_PROMPT = """You are an expert curriculum architect, teacher, and research librarian.
For the concept "{name}" tailored to a {level} learner, generate a comprehensive learning package.

Here are real web search results gathered for you:
{search_results}

Generate a single valid JSON object containing three main keys:
1. "roadmap": An interactive concept learning roadmap conforming to the following structure:
   - "summary": 3-4 sentence overview motivating the topic and previewing achievements.
   - "prerequisites": 2-3 short prerequisite topics.
   - "milestones": 7 to 9 milestones, ordered from foundations to mastery. Each milestone must contain:
     - "title": short, action-oriented milestone title.
     - "description": 2-3 sentences explaining learning outcomes.
     - "topics": 3-5 specific subtopics.
     - "key_questions": 2-3 thought-provoking questions answered by this milestone.
     - "exercise": exactly one concrete hands-on exercise (1-2 sentences).
     - "estimate": "~X hours"
   - "video_queries": 5-6 concrete YouTube search queries.
   - "search_queries": 5-7 focused web search queries.
   - "image_prompt": A clean, schematic, blueprint-style prompt representing the concept.
   - "study_guide_outline": List of 6-8 outline section titles.

2. "study_guide": A complete, in-depth study guide in Markdown. Do NOT summarize or return an outline; write the FULL content. It must include exactly these H2 headings:
   - ## Why this matters
   - ## Core ideas
   - ## How it actually works (step-by-step)
   - ## Worked example
   - ## Intuition & mental models
   - ## Common pitfalls and misconceptions
   - ## Going deeper (advanced angles)
   - ## Practice questions (6 questions, each with a 2-3 sentence answer below it)
   Note: The study guide content must be detailed and comprehensive (at least 1,100 words long).

3. "resources": Curated resource categories categorized from the search results and your own knowledge:
   - "categories": List of categories (e.g. "Official documentation", "In-depth articles & tutorials", "Free courses & lectures", "Books", "Research papers & whitepapers", "Tools, repos & playgrounds").
   - Each category must contain an "items" list.
   - Each item must have: "title", "url", "description" (1-2 sentences), and "kind" (one of: docs, article, course, book, paper, tool).
   - Only include categories that have at least 2 items. Categories must have 2-6 items.

Return ONLY raw JSON. No markdown fencing, no preamble, no trailing commentary.
"""

# ----------------------------- AI Services ---------------------------

ROADMAP_PROMPT = """You are an expert curriculum architect. For the concept "{name}" tailored to a {level} learner, produce a strictly valid JSON object.

Schema:
{{
  "summary": "3-4 sentence overview that motivates the topic and previews what the learner will achieve",
  "prerequisites": ["short prerequisite 1", "short prerequisite 2", "short prerequisite 3"],
  "milestones": [
    {{
      "title": "Milestone title (short, action-oriented)",
      "description": "2-3 sentences explaining what the learner will understand or build after this milestone",
      "topics": ["specific subtopic 1", "specific subtopic 2", "specific subtopic 3", "specific subtopic 4"],
      "key_questions": ["A thought-provoking question this milestone answers", "another key question", "another key question"],
      "exercise": "A concrete hands-on exercise or mini-project to cement the milestone (1-2 sentences)",
      "estimate": "~X hours"
    }}
  ],
  "video_queries": ["specific YouTube search query 1", "..."],
  "search_queries": ["focused web search query to find articles/docs about subtopic 1", "..."],
  "image_prompt": "A clean, schematic, blueprint-style illustration prompt that visually represents the concept, avoid text in image",
  "study_guide_outline": ["section 1", "section 2", "section 3", "section 4", "section 5", "section 6", "section 7"]
}}

Rules:
- Return ONLY raw JSON, no markdown fencing, no commentary.
- 7 to 9 milestones, ordered from foundations to mastery. Each milestone must be substantive — no trivial steps.
- Each milestone needs 3-5 topics, 2-3 key_questions, and exactly one exercise.
- 5 to 6 video_queries — concrete, learner-friendly YouTube search phrases.
- 5 to 7 search_queries — phrased like a researcher would search (e.g. "transformer attention math derivation", "REST vs gRPC tradeoffs").
- Adjust depth based on level: beginner = gentle scaffolding, intermediate = practical depth, advanced = expert-level nuance and edge cases.
"""

STUDY_GUIDE_PROMPT = """You are an expert teacher. Write an in-depth study guide for "{name}" tailored to a {level} learner.

Structure with these markdown sections (use exactly these H2 headings):
- ## Why this matters
- ## Core ideas
- ## How it actually works (step-by-step)
- ## Worked example
- ## Intuition & mental models
- ## Common pitfalls and misconceptions
- ## Going deeper (advanced angles)
- ## Practice questions

For "Practice questions": 6 questions, each with a 2-3 sentence answer below it.

Tone: clear, conversational but rigorous. Use bullet lists, numbered steps, and short code blocks where they help. Target 1100-1400 words. Output markdown only — no preamble, no closing remarks."""

RESOURCES_PROMPT = """You are an expert research librarian. For the concept "{name}" ({level} learner), here are real web search results gathered for you:

{search_results}

Task: From these results PLUS your own knowledge of canonical authoritative sources (e.g. official docs, MIT OCW, Stanford CS notes, Distill.pub, 3Blue1Brown, arXiv landmark papers, classic textbooks, Real Python, MDN, freeCodeCamp, etc.), build a curated, deduplicated resource library.

Return STRICTLY valid JSON, no markdown fencing:
{{
  "categories": [
    {{
      "name": "Official documentation",
      "items": [
        {{ "title": "Resource title (concise)", "url": "https://...", "description": "Why this is worth reading in 1-2 sentences", "kind": "docs" }}
      ]
    }},
    {{ "name": "In-depth articles & tutorials", "items": [...] }},
    {{ "name": "Free courses & lectures", "items": [...] }},
    {{ "name": "Books", "items": [...] }},
    {{ "name": "Research papers & whitepapers", "items": [...] }},
    {{ "name": "Tools, repos & playgrounds", "items": [...] }}
  ]
}}

Rules:
- Only include categories that have at least 2 high-quality items.
- 3-6 items per category. No duplicates, no broken-looking URLs, no spam aggregators.
- Prefer authoritative primary sources over content farms.
- For books, use a clear publisher/author page or "search:" entry (e.g. "https://www.google.com/search?q=Designing+Data+Intensive+Applications+book").
- For papers, use arxiv.org / acm.org / actual conference URLs when possible.
- "kind" must be one of: docs, article, course, book, paper, tool.
- Output ONLY raw JSON.
"""


def make_chat(session_id: str, system: str, provider: str = "gemini", model: str = None) -> LlmChat:
    if model is None:
        model = os.environ.get("LLM_MODEL") or "gemini-2.5-flash"
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=system,
    ).with_model(provider, model)


def extract_json(text: str) -> dict:
    # Strip code fences if present
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Find first { ... last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


async def generate_roadmap(name: str, level: str) -> dict:
    chat = make_chat(f"roadmap-{uuid.uuid4()}", "You are an expert curriculum architect. Always return strictly valid JSON.")
    msg = UserMessage(text=ROADMAP_PROMPT.format(name=name, level=level))
    reply = await chat.send_message(msg)
    return extract_json(reply)


async def generate_study_guide(name: str, level: str) -> str:
    chat = make_chat(f"guide-{uuid.uuid4()}", "You are an expert teacher writing study guides in markdown.")
    msg = UserMessage(text=STUDY_GUIDE_PROMPT.format(name=name, level=level))
    return await chat.send_message(msg)


async def generate_concept_image(prompt: str) -> Optional[str]:
    """Returns data URL string or None on failure."""
    try:
        img_model = os.environ.get("LLM_IMAGE_MODEL") or "gemini-2.5-flash"
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        chat = LlmChat(
            api_key=api_key,
            session_id=f"img-{uuid.uuid4()}",
            system_message="You generate clean schematic illustrations.",
        ).with_model("gemini", img_model).with_params(modalities=["image", "text"])
        msg = UserMessage(text=prompt)
        _, images = await chat.send_message_multimodal_response(msg)
        if images:
            img = images[0]
            return f"data:{img.get('mime_type', 'image/png')};base64,{img['data']}"
    except Exception as e:
        log.warning(f"image gen failed: {e}")
    return None


async def search_youtube(queries: List[str], per_query: int = 2) -> List[dict]:
    """Use yt-dlp to find videos without an API key. Runs in thread."""
    from yt_dlp import YoutubeDL

    def run():
        results = []
        seen = set()
        opts = {
            "quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": True, "default_search": "ytsearch",
            "noplaylist": True, "socket_timeout": 10,
        }
        with YoutubeDL(opts) as ydl:
            for q in queries[:6]:
                try:
                    info = ydl.extract_info(f"ytsearch{per_query}:{q}", download=False)
                    for entry in info.get("entries", [])[:per_query]:
                        vid = entry.get("id")
                        if not vid or vid in seen:
                            continue
                        seen.add(vid)
                        results.append({
                            "id": vid,
                            "title": entry.get("title") or "Untitled",
                            "channel": entry.get("channel") or entry.get("uploader") or "",
                            "duration": entry.get("duration"),
                            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "embed": f"https://www.youtube.com/embed/{vid}",
                            "query": q,
                        })
                except Exception as e:
                    log.warning(f"yt search '{q}' failed: {e}")
        return results
    return await asyncio.to_thread(run)


async def search_web(queries: List[str], per_query: int = 4) -> List[dict]:
    """DuckDuckGo text search (no API key). Aggregates results across queries."""
    from ddgs import DDGS
    # Silence noisy info-level engine errors from ddgs internals
    logging.getLogger("ddgs").setLevel(logging.ERROR)

    def run():
        results = []
        seen_urls = set()
        try:
            with DDGS(timeout=10) as d:
                for q in queries[:5]:
                    try:
                        for r in d.text(q, max_results=per_query, region="wt-wt", safesearch="moderate", backend="auto"):
                            url = r.get("href") or r.get("url")
                            if not url or url in seen_urls:
                                continue
                            seen_urls.add(url)
                            results.append({
                                "title": (r.get("title") or "").strip(),
                                "url": url,
                                "snippet": (r.get("body") or "").strip()[:240],
                                "query": q,
                            })
                    except Exception as e:
                        log.warning(f"ddg search '{q}' failed: {e}")
        except Exception as e:
            log.warning(f"ddg session failed: {e}")
        return results
    return await asyncio.to_thread(run)


async def generate_resources(name: str, level: str, search_queries: List[str]) -> dict:
    """Curate web search results into a categorized resource library via Claude."""
    if not search_queries:
        search_queries = [f"{name} tutorial", f"{name} documentation", f"{name} explained"]
    raw = await search_web(search_queries, per_query=4)
    if not raw:
        return {"categories": []}
    lines = []
    for i, r in enumerate(raw[:48]):
        lines.append(f"{i+1}. {r['title']} — {r['url']}\n   {r['snippet']}")
    block = "\n".join(lines)
    try:
        chat = make_chat(
            f"resources-{uuid.uuid4()}",
            "You are an expert research librarian. Always return strictly valid JSON.",
        )
        reply = await chat.send_message(UserMessage(
            text=RESOURCES_PROMPT.format(name=name, level=level, search_results=block)
        ))
        data = extract_json(reply)
        if "categories" not in data:
            data = {"categories": []}
        return data
    except Exception as e:
        log.warning(f"resources gen failed: {e}")
        return {
            "categories": [{
                "name": "Web results",
                "items": [
                    {"title": r["title"], "url": r["url"], "description": r["snippet"], "kind": "article"}
                    for r in raw[:12]
                ],
            }]
        }


# ----------------------------- Routes: Auth --------------------------

@api.get("/")
async def root():
    return {"name": "ConceptForge API", "ok": True}

@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": email,
        "name": body.name.strip(),
        "password_hash": hash_password(body.password),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_access_token(user_id, email)
    set_auth_cookie(response, token)
    return {"id": user_id, "email": email, "name": doc["name"], "token": token}

@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], email)
    set_auth_cookie(response, token)
    return {"id": user["id"], "email": email, "name": user.get("name", ""), "token": token}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ----------------------------- Routes: Concepts ----------------------

async def _run_concept_generation(concept_id: str, user_id: str, name: str, level: str):
    """Background task — runs the consolidated structured generation pipeline.

    Pipeline:
      1. Web Search & YouTube Search executed in parallel (t=0).
      2. Web search results compressed to top 12 to reduce prompt token footprint.
      3. A single structured LLM call requested using response_format=ConceptResponseSchema.
      4. Structured JSON response parsed and validated (with a fallback retry on validation failure).
      5. Concepts collection updated atomically while preserving stage transitions.
    """
    try:
        # Phase 1 — start non-LLM tasks in parallel
        prelim_video_queries = [f"{name} tutorial", f"{name} explained", f"{name} crash course"]
        prelim_web_queries = [f"{name} guide", f"{name} documentation", f"{name} introduction", f"{name} tutorial"]

        video_task = asyncio.create_task(search_youtube(prelim_video_queries))
        web_task = asyncio.create_task(search_web(prelim_web_queries, per_query=4))

        # Wait for web search results to finish so they can be injected as context
        web_results = await web_task

        # Compress results to top 12 to minimize prompt size and keep TPM low
        compressed_results = web_results[:12] if web_results else []
        lines = [f"{i+1}. {r['title']} — {r['url']}\n   {r['snippet']}" for i, r in enumerate(compressed_results)]
        search_text = "\n".join(lines)

        # Build the consolidated prompt
        chat = make_chat(
            f"gen-{uuid.uuid4()}",
            "You are an expert curriculum architect, teacher, and research librarian. Always return strictly valid JSON matching the requested schema.",
        )
        chat.with_params(
            response_format=ConceptResponseSchema,
        )

        prompt_text = CONSOLIDATED_CONCEPT_PROMPT.format(
            name=name,
            level=level,
            search_results=search_text
        )

        max_llm_attempts = 2
        validated_data = None

        for attempt in range(max_llm_attempts):
            try:
                reply = await chat.send_message(UserMessage(text=prompt_text))
                raw_json = extract_json(reply)
                # Pydantic validation
                validated_data = ConceptResponseSchema(**raw_json)
                break
            except Exception as e:
                log.warning(f"Consolidated concept generation attempt {attempt + 1} failed: {e}")
                if attempt == max_llm_attempts - 1:
                    raise
                # Update instructions to request strictly valid schema
                prompt_text += "\n\nCRITICAL: Your previous response was invalid JSON or did not match the requested schema structure. Return ONLY a single valid JSON object matching the requested schema."

        # Extract Pydantic model dicts
        roadmap = validated_data.roadmap.model_dump()
        study_guide = validated_data.study_guide
        resources = validated_data.resources.model_dump()

        # Enforce that categories containing fewer than 2 items are filtered out
        if "categories" in resources:
            resources["categories"] = [
                cat for cat in resources["categories"]
                if isinstance(cat.get("items"), list) and len(cat["items"]) >= 2
            ]

        # Use direct transparent placeholder for concept image (gemini has no text-to-image out of the box)
        image_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

        # Transition stage to expanding
        await db.concepts.update_one(
            {"id": concept_id, "user_id": user_id},
            {"$set": {"roadmap": roadmap, "stage": "expanding"}},
        )

        # Wait for video search to finish
        videos = await video_task

        # Atomic final database update
        await db.concepts.update_one(
            {"id": concept_id, "user_id": user_id},
            {"$set": {
                "study_guide": study_guide,
                "image": image_data_url,
                "videos": videos,
                "resources": resources,
                "status": "ready",
                "stage": "done",
                "ready_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        log.info(f"Concept '{name}' ({concept_id}) ready.")
    except Exception as e:
        log.exception(f"concept generation failed for {concept_id}")
        await db.concepts.update_one(
            {"id": concept_id, "user_id": user_id},
            {"$set": {"status": "failed", "error": str(e)[:240]}},
        )


@api.post("/concepts/generate")
async def generate_concept(body: GenerateIn, user: dict = Depends(get_current_user)):
    name = body.name.strip()
    level = body.level
    log.info(f"Queuing concept '{name}' for {user['email']} ({level})")

    concept_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    initial = {
        "id": concept_id,
        "user_id": user["id"],
        "name": name,
        "level": level,
        "status": "generating",
        "stage": "roadmap",
        "roadmap": None,
        "study_guide": None,
        "image": None,
        "videos": [],
        "resources": None,
        "progress": [],
        "created_at": now,
    }
    await db.concepts.insert_one(initial.copy())
    # Kick off background task and keep a strong reference to prevent GC deletion
    gen_task = asyncio.create_task(_run_concept_generation(concept_id, user["id"], name, level))
    active_tasks.add(gen_task)
    gen_task.add_done_callback(active_tasks.discard)
    return {"id": concept_id, "status": "generating", "stage": "roadmap"}

@api.get("/concepts")
async def list_concepts(user: dict = Depends(get_current_user)):
    cursor = db.concepts.find(
        {"user_id": user["id"]},
        {"_id": 0, "study_guide": 0, "videos": 0, "image": 0, "resources": 0,
         "roadmap.summary": 0, "roadmap.prerequisites": 0, "roadmap.study_guide_outline": 0,
         "roadmap.video_queries": 0, "roadmap.search_queries": 0, "roadmap.image_prompt": 0},
    ).sort("created_at", -1)
    items = await cursor.to_list(200)
    for it in items:
        milestones = (it.get("roadmap") or {}).get("milestones") or []
        it["milestone_count"] = len(milestones)
        it["progress"] = it.get("progress") or []
        it.setdefault("status", "ready")
        it.pop("roadmap", None)
    return items

@api.get("/concepts/{concept_id}")
async def get_concept(concept_id: str, user: dict = Depends(get_current_user)):
    doc = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Concept not found")
    doc.setdefault("progress", [])
    return doc

@api.patch("/concepts/{concept_id}/progress")
async def update_progress(concept_id: str, body: ProgressIn, user: dict = Depends(get_current_user)):
    doc = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0, "progress": 1, "roadmap": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Concept not found")
    milestones = (doc.get("roadmap") or {}).get("milestones") or []
    if body.index >= len(milestones):
        raise HTTPException(status_code=400, detail="Milestone index out of range")
    current = set(doc.get("progress") or [])
    if body.completed:
        current.add(body.index)
    else:
        current.discard(body.index)
    new_progress = sorted(current)
    await db.concepts.update_one(
        {"id": concept_id, "user_id": user["id"]},
        {"$set": {"progress": new_progress}},
    )
    return {"id": concept_id, "progress": new_progress, "total": len(milestones)}

@api.delete("/concepts/{concept_id}")
async def delete_concept(concept_id: str, user: dict = Depends(get_current_user)):
    res = await db.concepts.delete_one({"id": concept_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Concept not found")
    await db.chat_messages.delete_many({"concept_id": concept_id})
    return {"ok": True}


def _build_concept_markdown(c: dict) -> str:
    """Render a saved concept doc into a self-contained Markdown document."""
    name = c.get("name", "Untitled")
    level = c.get("level", "")
    rm = c.get("roadmap") or {}
    milestones = rm.get("milestones") or []
    progress = set(c.get("progress") or [])
    out = []
    out.append(f"# {name}\n")
    out.append(f"_Level: **{level}** · Generated by ConceptForge_\n")
    if rm.get("summary"):
        out.append("## Summary\n")
        out.append(rm["summary"].strip() + "\n")
    if rm.get("prerequisites"):
        out.append("## Prerequisites\n")
        for p in rm["prerequisites"]:
            out.append(f"- {p}")
        out.append("")

    if milestones:
        out.append("## Roadmap\n")
        for i, m in enumerate(milestones):
            done = "✅" if i in progress else "⬜"
            est = f" _(_{m.get('estimate','')}_)_" if m.get("estimate") else ""
            out.append(f"### {done} {i+1:02d}. {m.get('title','Milestone')}{est}\n")
            if m.get("description"):
                out.append(m["description"].strip() + "\n")
            if m.get("topics"):
                out.append("**Topics:** " + ", ".join(m["topics"]) + "\n")
            if m.get("key_questions"):
                out.append("**Key questions:**")
                for q in m["key_questions"]:
                    out.append(f"- {q}")
                out.append("")
            if m.get("exercise"):
                out.append(f"**Exercise:** {m['exercise']}\n")

    if c.get("study_guide"):
        out.append("\n---\n\n# Study Guide\n")
        out.append(c["study_guide"].strip())

    cats = (c.get("resources") or {}).get("categories") or []
    if cats:
        out.append("\n---\n\n# Resources\n")
        for cat in cats:
            out.append(f"\n## {cat.get('name','Resources')}\n")
            for it in (cat.get("items") or []):
                title = it.get("title", "").strip()
                url = it.get("url", "").strip()
                desc = (it.get("description") or "").strip()
                line = f"- [{title}]({url})"
                if desc:
                    line += f" — {desc}"
                out.append(line)

    videos = c.get("videos") or []
    if videos:
        out.append("\n---\n\n# Videos\n")
        for v in videos:
            out.append(f"- [{v.get('title','')}]({v.get('url','')}) · _{v.get('channel','')}_")

    out.append("\n---\n_Exported from ConceptForge._\n")
    return "\n".join(out)


def _markdown_to_pdf_html(md_text: str, title: str) -> str:
    body_html = md_lib.markdown(md_text, extensions=["extra", "sane_lists", "tables"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>
  @page {{ size: A4; margin: 22mm 18mm; }}
  body {{ font-family: 'Helvetica', sans-serif; font-size: 11pt; color: #18181b; line-height: 1.55; }}
  h1 {{ font-size: 26pt; margin: 0 0 4pt; border-bottom: 2px solid #002FA7; padding-bottom: 6pt; }}
  h2 {{ font-size: 16pt; margin: 22pt 0 6pt; color: #002FA7; }}
  h3 {{ font-size: 12pt; margin: 14pt 0 4pt; }}
  p  {{ margin: 6pt 0; }}
  ul, ol {{ margin: 4pt 0 4pt 16pt; }}
  li {{ margin: 2pt 0; }}
  hr {{ border: 0; border-top: 1px solid #d4d4d8; margin: 18pt 0; }}
  code {{ background: #f4f4f5; padding: 1pt 4pt; border-radius: 2pt; font-family: 'Menlo','Consolas',monospace; font-size: 10pt; }}
  strong {{ color: #002FA7; }}
  a {{ color: #002FA7; text-decoration: none; word-break: break-word; }}
  blockquote {{ border-left: 3px solid #002FA7; padding-left: 10pt; color: #52525b; }}
</style></head><body>{body_html}</body></html>"""


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\- ]+", "", s).strip().replace(" ", "_")
    return s[:80] or "concept"


@api.get("/concepts/{concept_id}/export")
async def export_concept(
    concept_id: str,
    format: str = "md",
    user: dict = Depends(get_current_user),
):
    if format not in {"md", "pdf"}:
        raise HTTPException(status_code=400, detail="format must be md or pdf")
    doc = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Concept not found")
    if doc.get("status") not in (None, "ready"):
        raise HTTPException(status_code=409, detail="Concept is not ready yet")

    md_text = _build_concept_markdown(doc)
    fname_base = _safe_filename(doc.get("name", "concept"))

    if format == "md":
        return PlainTextResponse(
            md_text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{fname_base}.md"'},
        )

    # PDF
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        log.warning(f"weasyprint not available: {e}")
        raise HTTPException(status_code=501, detail="PDF export is not available on this server. Use markdown export instead.")
    html = _markdown_to_pdf_html(md_text, doc.get("name", "Concept"))
    pdf_bytes = await asyncio.to_thread(lambda: HTML(string=html).write_pdf())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname_base}.pdf"'},
    )

# ----------------------------- Routes: Tutor Chat --------------------

@api.get("/concepts/{concept_id}/chat")
async def get_chat(concept_id: str, user: dict = Depends(get_current_user)):
    concept = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0, "name": 1})
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    cursor = db.chat_messages.find({"concept_id": concept_id, "user_id": user["id"]}, {"_id": 0}).sort("created_at", 1)
    msgs = await cursor.to_list(500)
    return msgs

@api.post("/concepts/{concept_id}/chat")
async def post_chat(concept_id: str, body: ChatIn, user: dict = Depends(get_current_user)):
    concept = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0})
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Save user message
    user_msg = {
        "id": str(uuid.uuid4()),
        "concept_id": concept_id,
        "user_id": user["id"],
        "role": "user",
        "content": body.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.chat_messages.insert_one(user_msg.copy())

    # Load prior history
    history = await db.chat_messages.find(
        {"concept_id": concept_id, "user_id": user["id"]},
        {"_id": 0, "role": 1, "content": 1},
    ).sort("created_at", 1).to_list(40)

    system = (
        f"You are a patient, expert tutor helping a {concept['level']} learner master '{concept['name']}'. "
        f"Adapt your explanations to their level. Be concise but thorough. "
        f"Use analogies, examples, and check their understanding. Reference the roadmap milestones when relevant: "
        f"{[m.get('title') for m in (concept.get('roadmap') or {}).get('milestones', [])]}"
    )

    # Append random string to session_id to make it unique per message.
    # This keeps proxy calls stateless so we don't get double history duplication (since we pass manual context).
    session_id = f"tutor-{concept_id}-{uuid.uuid4().hex}"
    chat = make_chat(session_id, system)

    # Replay last user-assistant pairs as a single context block to avoid library state issues
    context_blocks = []
    for m in history[:-1]:  # exclude the just-inserted user message
        prefix = "USER" if m["role"] == "user" else "ASSISTANT"
        context_blocks.append(f"{prefix}: {m['content']}")
    context = "\n\n".join(context_blocks)
    prompt_text = (f"Conversation so far:\n{context}\n\nUSER: {body.message}\n\nASSISTANT:"
                   if context else body.message)

    try:
        reply = await chat.send_message(UserMessage(text=prompt_text))
    except Exception as e:
        log.exception("tutor reply failed")
        raise HTTPException(status_code=502, detail=f"Tutor failed: {e}")

    asst_msg = {
        "id": str(uuid.uuid4()),
        "concept_id": concept_id,
        "user_id": user["id"],
        "role": "assistant",
        "content": reply,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.chat_messages.insert_one(asst_msg.copy())
    return {"user": user_msg, "assistant": asst_msg}

# ----------------------------- Startup -------------------------------

@app.on_event("startup")
async def on_startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.concepts.create_index([("user_id", 1), ("created_at", -1)])
        await db.chat_messages.create_index([("concept_id", 1), ("created_at", 1)])

        # Seed admin
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@conceptforge.app").lower()
        admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "email": admin_email,
                "name": "Admin",
                "password_hash": hash_password(admin_pw),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            log.info(f"Seeded admin {admin_email}")
        elif not verify_password(admin_pw, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})
    except Exception as e:
        log.error(f"Startup DB init failed (server will continue): {e}")

@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api)

cors_origins_str = os.environ.get('CORS_ORIGINS', '')
cors_origins = [orig.strip() for orig in cors_origins_str.split(',') if orig.strip()] if cors_origins_str else []
if not cors_origins:
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://conceptforge.onrender.com",
        "https://concept-4wnq.onrender.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
