import os
import tempfile
import uuid
from urllib.parse import quote

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from .agent import get_opening_message, get_response
from .call_manager import get_call_status, place_outbound_call
from .twilio_handler import (
    make_gather_response,
    make_voicemail_response,
    make_end_call_response
)
from .voice_in import speech_to_text
from .voice_out import text_to_speech

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")  # your ngrok URL
_TMP_DIR = tempfile.gettempdir()


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

# ── Endpoint 1: Trigger a real outbound call ──────────────────────────────
@app.post("/initiate-call")
async def initiate_call(
    customer_phone: str,
    customer_name: str = "Valued Customer"
):
    """Place a real Twilio outbound call to customer_phone."""
    if not WEBHOOK_BASE_URL:
        raise HTTPException(
            status_code=500,
            detail="WEBHOOK_BASE_URL not set in .env"
        )
    try:
        call_sid = place_outbound_call(
            customer_phone, customer_name, WEBHOOK_BASE_URL
        )
        return {"call_sid": call_sid, "status": "initiated"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


# ── Endpoint 2: Twilio calls this when customer picks up ─────────────────
@app.post("/twilio-answer", response_class=PlainTextResponse)
async def twilio_answer(customer_name: str = "Valued Customer"):
    """Twilio webhook — called when customer picks up."""
    if not WEBHOOK_BASE_URL:
        raise HTTPException(status_code=500, detail="WEBHOOK_BASE_URL not set in .env")

    session_id = _make_session_id()
    opening_text, history = get_opening_message(customer_name)

    # Generate ElevenLabs audio and save as accessible URL
    audio_bytes = text_to_speech(opening_text)
    audio_filename = f"{session_id}_opening.mp3"
    audio_path = os.path.join(_TMP_DIR, audio_filename)

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    sessions[session_id] = {
        "history": history,
        "customer_name": customer_name
    }

    audio_url = f"{WEBHOOK_BASE_URL}/audio/{audio_filename}"
    action_url = f"{WEBHOOK_BASE_URL}/twilio-voice-input?session_id={session_id}"

    twiml = make_gather_response(
        speech_text=opening_text,
        action_url=action_url,
        voice_url=audio_url
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")


# ── Endpoint 3: Twilio sends customer's speech here ──────────────────────
@app.post("/twilio-voice-input", response_class=PlainTextResponse)
async def twilio_voice_input(
    session_id: str,
    SpeechResult: str = Form(""),       # Twilio sends transcribed speech here
    AnsweredBy: str = Form("human")     # "machine_start" = voicemail
):
    """Twilio webhook — called after customer speaks."""
    if not WEBHOOK_BASE_URL:
        raise HTTPException(status_code=500, detail="WEBHOOK_BASE_URL not set in .env")

    # Handle voicemail
    if AnsweredBy == "machine_start":
        session = sessions.get(session_id, {})
        name = session.get("customer_name", "")
        return PlainTextResponse(
            content=make_voicemail_response(name),
            media_type="application/xml"
        )

    if session_id not in sessions:
        return PlainTextResponse(
            content=make_end_call_response(),
            media_type="application/xml"
        )

    if not SpeechResult.strip():
        # Re-prompt if no speech detected
        action_url = f"{WEBHOOK_BASE_URL}/twilio-voice-input?session_id={session_id}"
        reprompt_text = "Mujhe aapki awaaz nahi aayi, kya aap dobara bol sakte hain?"
        twiml = make_gather_response(
            speech_text=reprompt_text,
            action_url=action_url,
            voice_url=None
        )
        return PlainTextResponse(content=twiml, media_type="application/xml")

    session = sessions[session_id]
    ai_text, updated_history = get_response(
        session["history"],
        SpeechResult,
        customer_name=session["customer_name"]
    )
    sessions[session_id]["history"] = updated_history

    # End call only if user's speech contains clear goodbye phrases
    goodbye_phrases = [
        "bye", "alvida", "band karo", "call khatam", "baad mein baat"
    ]
    if any(phrase in SpeechResult.lower() for phrase in goodbye_phrases):
        return PlainTextResponse(
            content=make_end_call_response(),
            media_type="application/xml"
        )

    audio_bytes = text_to_speech(ai_text)
    audio_filename = f"{session_id}_{len(session['history'])}.mp3"
    audio_path = os.path.join(_TMP_DIR, audio_filename)

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    audio_url = f"{WEBHOOK_BASE_URL}/audio/{audio_filename}"
    action_url = f"{WEBHOOK_BASE_URL}/twilio-voice-input?session_id={session_id}"

    twiml = make_gather_response(
        speech_text=ai_text,
        action_url=action_url,
        voice_url=audio_url
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")


# ── Endpoint 4: Serve audio files to Twilio ──────────────────────────────
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated MP3 files so Twilio can play them."""
    safe_name = os.path.basename(filename)
    audio_path = os.path.join(_TMP_DIR, safe_name)
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ── Endpoint 5: Check call status ────────────────────────────────────────
@app.get("/call-status/{call_sid}")
async def check_call_status(call_sid: str):
    """Check the status of a placed call."""
    try:
        status = get_call_status(call_sid)
        return {"call_sid": call_sid, "status": status}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


# Mount frontend LAST so the API routes above are never shadowed.
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")