# set up api
import json
import os
import re
import threading
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from transcript import fetch_transcript_openai, fetch_transcript_youtube
import vectorStore

load_dotenv()

app = FastAPI()

# Reuse a single OpenAI client for the whole process.
openai_client = OpenAI()

# ---------------------------------------------------------------------------
# Config (all overridable via environment variables)
# ---------------------------------------------------------------------------
# If API_KEY is unset we run "open" (dev mode). Set it in production so random
# traffic hitting the public URL can't drain the OpenAI account.
API_KEY = os.getenv("API_KEY")
# Per-IP sliding-window rate limit. In-memory, so this assumes a single worker
# (the default for our uvicorn command). Move to Redis if we scale out.
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Chat model (configurable so it can be swapped without a code change).
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5")
# The extension over-fetches candidates (n_results) for good recall, but only
# the most relevant, de-duplicated few are actually sent to the LLM. This is
# the main lever on recurring per-question token cost.
MAX_CONTEXT_CHUNKS = int(os.getenv("MAX_CONTEXT_CHUNKS", "8"))

# CORS: allow the YouTube page and the extension itself. allow_credentials is
# False because we authenticate with a header, not cookies — the old
# ["*"] + allow_credentials=True combination is rejected by browsers anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https://www\.youtube\.com|chrome-extension://.*)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth + rate limiting (used as FastAPI dependencies)
# ---------------------------------------------------------------------------
def require_api_key(x_api_key: str = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


_rate_buckets = defaultdict(deque)
_rate_lock = threading.Lock()


def rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, please slow down.",
            )
        bucket.append(now)


class TranscriptRequest(BaseModel):
    video_id: str


class QuestionRequest(BaseModel):
    video_id: str
    question: str
    n_results: int


# ---------------------------------------------------------------------------
# Transcript loading as a background job
# ---------------------------------------------------------------------------
# Keyed by video_id so concurrent requests for the same video dedupe for free
# instead of each downloading + transcribing + embedding (double billing).
_jobs = {}  # video_id -> {"status": str, "detail": str}
_jobs_lock = threading.Lock()

# Statuses the frontend polls on: pending, loading_captions, transcribing,
# ready, error.
_IN_PROGRESS = {"pending", "loading_captions", "transcribing"}


def _set_status(video_id, status, detail=""):
    with _jobs_lock:
        _jobs[video_id] = {"status": status, "detail": detail}


def _run_load_job(video_id: str):
    try:
        if vectorStore.check_exists(video_id):
            _set_status(video_id, "ready")
            return

        _set_status(video_id, "loading_captions")
        try:
            transcript = fetch_transcript_youtube(video_id)
        except Exception as e:
            # No usable captions — fall back to the (slow) audio + Whisper path.
            print(f"Caption fetch failed ({e}); falling back to Whisper")
            _set_status(video_id, "transcribing")
            transcript = fetch_transcript_openai(video_id)

        chunks = vectorStore.split_text_to_chunks(transcript)
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [{"start": c["start"], "end": c["end"]} for c in chunks]
        vectorStore.store_chunks(video_id, texts, metadatas)

        if not vectorStore.check_exists(video_id):
            _set_status(video_id, "error", "No transcript content could be stored.")
            return
        _set_status(video_id, "ready")
    except Exception as e:
        print("Transcript job failed:", e)
        _set_status(video_id, "error", str(e))


@app.get("/")
def test():
    return {"status": "ok"}


@app.post("/load_transcript")
def load_transcript(
    req: TranscriptRequest,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(require_api_key),
    _rl: None = Depends(rate_limit),
):
    video_id = req.video_id
    with _jobs_lock:
        existing = _jobs.get(video_id)
        if existing and existing["status"] in _IN_PROGRESS:
            return {"video_id": video_id, "status": existing["status"]}
        # Already embedded from a previous session — nothing to do.
        if vectorStore.check_exists(video_id):
            _jobs[video_id] = {"status": "ready", "detail": ""}
            return {"video_id": video_id, "status": "ready"}
        _jobs[video_id] = {"status": "pending", "detail": ""}

    background_tasks.add_task(_run_load_job, video_id)
    return {"video_id": video_id, "status": "pending"}


@app.get("/transcript_status/{video_id}")
def transcript_status(
    video_id: str,
    _auth: None = Depends(require_api_key),
    _rl: None = Depends(rate_limit),
):
    return _jobs.get(video_id, {"status": "unknown", "detail": ""})


# ---------------------------------------------------------------------------
# Question answering (streamed)
# ---------------------------------------------------------------------------
def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _select_context(docs: list, metas: list, max_chunks: int) -> list:
    """Trim retrieved chunks down to the most relevant, unique few before they
    hit the LLM. Chroma returns results already sorted by similarity (most
    relevant first), so we take from the front, skipping empty and duplicate
    text. Returns a list of {"start", "text"}."""
    selected = []
    seen = set()
    for doc, meta in zip(docs, metas):
        text = (doc or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:  # drop exact-duplicate chunks (common with small chunks)
            continue
        seen.add(key)
        selected.append({"start": meta.get("start"), "text": text})
        if len(selected) >= max_chunks:
            break
    return selected


def _build_citations(full_text: str, context: list) -> list:
    """Map the model's cited timestamps back to the chunk text they came from
    so the UI can show *what* supports each timestamp, not just a bare link."""
    match = re.search(r"TIMESTAMPS:\s*(.+)", full_text, re.S | re.I)
    if not match:
        return []
    raw = match.group(1).strip()
    if raw.lower().startswith("none"):
        return []

    citations = []
    seen = set()
    for token in raw.split(","):
        numbers = re.findall(r"[\d.]+", token)
        if not numbers:
            continue
        try:
            seconds = float(numbers[0])
        except ValueError:
            continue
        seconds_int = int(seconds)
        if seconds_int in seen:
            continue
        seen.add(seconds_int)

        # Find the context chunk whose start time is closest to this cite.
        best_i, best_dist = None, None
        for i, chunk in enumerate(context):
            start = chunk.get("start")
            if start is None:
                continue
            dist = abs(start - seconds)
            if best_dist is None or dist < best_dist:
                best_dist, best_i = dist, i

        snippet = context[best_i]["text"].strip() if best_i is not None else ""
        if len(snippet) > 160:
            snippet = snippet[:160].rstrip() + "…"
        citations.append({"seconds": seconds_int, "snippet": snippet})
    return citations


@app.post("/ask_question")
def ask_question(
    req: QuestionRequest,
    _auth: None = Depends(require_api_key),
    _rl: None = Depends(rate_limit),
):
    results = vectorStore.query_chunks(req.video_id, req.question, req.n_results)
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    context = _select_context(docs, metas, MAX_CONTEXT_CHUNKS)

    if not context:
        def empty_gen():
            yield _sse(
                {
                    "type": "token",
                    "text": "The transcript for this video isn't ready yet. "
                    "Please wait for it to finish loading and try again.",
                }
            )
            yield _sse({"type": "citations", "citations": []})
            yield "data: [DONE]\n\n"

        return StreamingResponse(empty_gen(), media_type="text/event-stream")

    # Compact context: one line per excerpt, prefixed with its start time in
    # seconds. Far fewer tokens than dumping Python list/dict reprs, and easier
    # for the model to cite from.
    context_lines = "\n".join(
        f"[{int(c['start'])}s] {c['text']}"
        for c in context
        if c["start"] is not None
    )

    prompt = f"""Based on the following transcript excerpts from a YouTube video,
    answer the user's question using the provided context and inferring additional context if there are
    any inaccuracies or more details are needed. Only provide the answer to the question, the rest of the response is not needed. Provide a response if
    no relevant information was found for the user (please provide a layer of transparency between the tool workings and the user, do not say things like transcript chunks).
    Each excerpt is prefixed with its start time in seconds, e.g. [123s].

    User question: {req.question}

    Transcript excerpts:
    {context_lines}

    IMPORTANT: After your answer, list the timestamps (the [Ns] values) that directly support your answer. Please don't just only try to match
    the chunks that have the most matched words to the user's question but actually what you can infer gives the most accurate and context to the question.
    Please respond in TIMESTAMPS: times go here in seconds seperated by commas and by order of relevance (most relevant chunk goes first). If no specific timestamps are relevant, write: TIMESTAMPS: none"""

    def gen():
        full = ""
        try:
            stream = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                stream=True,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant to aid users when asking questions about videos.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full += delta
                    yield _sse({"type": "token", "text": delta})

            citations = _build_citations(full, context)
            yield _sse({"type": "citations", "citations": citations})
            yield "data: [DONE]\n\n"
        except Exception as e:
            print("ask_question stream failed:", e)
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")
