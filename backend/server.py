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

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Body
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage

# ----------------------------- Setup ---------------------------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = 'HS256'

app = FastAPI(title="ConceptForge API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("conceptforge")

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

# ----------------------------- AI Services ---------------------------

ROADMAP_PROMPT = """You are an expert curriculum architect. For the concept "{name}" tailored to a {level} learner, produce a strictly valid JSON object.

Schema:
{{
  "summary": "2-3 sentence overview of what the learner will achieve",
  "prerequisites": ["short prerequisite 1", "short prerequisite 2"],
  "milestones": [
    {{
      "title": "Milestone title (short)",
      "description": "1-2 sentences explaining the milestone",
      "topics": ["topic 1", "topic 2", "topic 3"],
      "estimate": "~X hours"
    }}
  ],
  "video_queries": ["specific YouTube search query 1", "..."],
  "image_prompt": "A clean, schematic, blueprint-style illustration prompt that visually represents the concept, avoid text in image",
  "study_guide_outline": ["section 1", "section 2", "section 3", "section 4", "section 5"]
}}

Rules:
- Return ONLY raw JSON, no markdown fencing, no commentary.
- 5 to 7 milestones, ordered from foundations to mastery.
- 4 to 6 video_queries — concrete, learner-friendly YouTube search phrases.
- Adjust depth based on level: beginner = gentle, advanced = expert-level.
"""

STUDY_GUIDE_PROMPT = """You are an expert teacher. Write a detailed study guide for "{name}" for a {level} learner.

Structure with these markdown sections:
- ## Why this matters
- ## Core ideas
- ## Step-by-step explanation
- ## Worked example
- ## Common pitfalls
- ## Practice questions (5 questions with brief answers)

Tone: clear, conversational but rigorous. Use bullet lists where helpful. ~700-900 words. Output markdown only."""


def make_chat(session_id: str, system: str, provider: str = "anthropic", model: str = "claude-sonnet-4-6") -> LlmChat:
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
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
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"img-{uuid.uuid4()}",
            system_message="You generate clean schematic illustrations.",
        ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
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

@api.post("/concepts/generate")
async def generate_concept(body: GenerateIn, user: dict = Depends(get_current_user)):
    name = body.name.strip()
    level = body.level
    log.info(f"Generating concept '{name}' for {user['email']} ({level})")

    # Run roadmap first (we need its prompts/queries to feed image + videos)
    try:
        roadmap = await generate_roadmap(name, level)
    except Exception as e:
        log.exception("roadmap failed")
        raise HTTPException(status_code=502, detail=f"Roadmap generation failed: {e}")

    # Run study guide, image, videos in parallel
    img_prompt = roadmap.get("image_prompt") or f"Schematic blueprint illustration of {name}"
    queries = roadmap.get("video_queries") or [f"{name} tutorial", f"{name} explained"]

    guide_task = asyncio.create_task(generate_study_guide(name, level))
    image_task = asyncio.create_task(generate_concept_image(img_prompt))
    video_task = asyncio.create_task(search_youtube(queries))

    study_guide, image_data_url, videos = await asyncio.gather(guide_task, image_task, video_task)

    concept_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": concept_id,
        "user_id": user["id"],
        "name": name,
        "level": level,
        "roadmap": roadmap,
        "study_guide": study_guide,
        "image": image_data_url,
        "videos": videos,
        "created_at": now,
    }
    await db.concepts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/concepts")
async def list_concepts(user: dict = Depends(get_current_user)):
    cursor = db.concepts.find(
        {"user_id": user["id"]},
        {"_id": 0, "study_guide": 0, "videos": 0, "roadmap": 0},
    ).sort("created_at", -1)
    items = await cursor.to_list(200)
    return items

@api.get("/concepts/{concept_id}")
async def get_concept(concept_id: str, user: dict = Depends(get_current_user)):
    doc = await db.concepts.find_one({"id": concept_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Concept not found")
    return doc

@api.delete("/concepts/{concept_id}")
async def delete_concept(concept_id: str, user: dict = Depends(get_current_user)):
    res = await db.concepts.delete_one({"id": concept_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Concept not found")
    await db.chat_messages.delete_many({"concept_id": concept_id})
    return {"ok": True}

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
        f"{[m.get('title') for m in concept['roadmap'].get('milestones', [])]}"
    )

    session_id = f"tutor-{concept_id}"
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

@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
