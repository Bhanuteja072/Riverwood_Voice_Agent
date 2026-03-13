import os
import uuid
from urllib.parse import quote

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .agent import get_response, get_opening_message
from .voice_in import speech_to_text
from .voice_out import text_to_speech

app = FastAPI(title="Riverwood Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # explicit — avoids footgun if origins are tightened later
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-ID", "X-Agent-Text", "X-User-Text"],
)

# In-memory session store: {session_id: {"history": [...], "customer_name": str}}
# Replace with Redis for multi-worker / production deployments.
sessions: dict[str, dict[str, object]] = {}


def _make_session_id() -> str:
    """Collision-free session ID using UUID4."""
    return f"session_{uuid.uuid4().hex}"


def _encode_header(value: str) -> str:
    """Percent-encode a string so it is safe inside an HTTP header value."""
    return quote(value, safe="")


@app.post("/start-call")
async def start_call(customer_name: str = "Valued Customer"):
    """Start a new call session — returns opening MP3 audio."""
    session_id = _make_session_id()

    try:
        opening_text, history = get_opening_message(customer_name)
        audio_bytes = text_to_speech(opening_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent/TTS error: {exc}")

    sessions[session_id] = {"history": history, "customer_name": customer_name}

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Session-ID": session_id,
            "X-Agent-Text": _encode_header(opening_text),
        },
    )


@app.post("/respond-voice")
async def respond_voice(session_id: str, audio: UploadFile = File(...)):
    """Transcribe uploaded audio, get agent reply, return MP3 audio."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_bytes = await audio.read()

    try:
        user_text = speech_to_text(audio_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Transcription error: {exc}")

    if not user_text.strip():
        raise HTTPException(status_code=422, detail="No speech detected in audio.")

    session = sessions[session_id]
    try:
        ai_text, updated_history = get_response(
            session["history"], user_text, customer_name=session["customer_name"]
        )
        audio_response = text_to_speech(ai_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent/TTS error: {exc}")

    sessions[session_id]["history"] = updated_history

    return Response(
        content=audio_response,
        media_type="audio/mpeg",
        headers={
            "X-User-Text": _encode_header(user_text),
            "X-Agent-Text": _encode_header(ai_text),
            "X-Session-ID": session_id,
        },
    )


@app.post("/respond-text")
async def respond_text(session_id: str, message: str):
    """Accept text input, get GPT reply, return MP3 audio."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not message.strip():
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    session = sessions[session_id]
    try:
        ai_text, updated_history = get_response(
            session["history"], message, customer_name=session["customer_name"]
        )
        audio_response = text_to_speech(ai_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent/TTS error: {exc}")

    sessions[session_id]["history"] = updated_history

    return Response(
        content=audio_response,
        media_type="audio/mpeg",
        headers={
            "X-Agent-Text": _encode_header(ai_text),
            "X-Session-ID": session_id,
        },
    )


# Mount frontend LAST so the API routes above are never shadowed.
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")