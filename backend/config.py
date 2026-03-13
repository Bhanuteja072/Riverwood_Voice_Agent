import os
import warnings
from dotenv import load_dotenv

# Load variables from a .env file in the project root (no-op if file is absent)
load_dotenv()

# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
# Default voice: ElevenLabs "Rachel" (multilingual v2)
ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# ---------------------------------------------------------------------------
# TTS Mode: "elevenlabs" or "gtts" (gtts is fully free fallback)
# ---------------------------------------------------------------------------
TTS_MODE: str = os.getenv("TTS_MODE", "elevenlabs").strip().lower()
if TTS_MODE not in {"elevenlabs", "gtts"}:
    warnings.warn(
        f"Unknown TTS_MODE '{TTS_MODE}'. Falling back to 'elevenlabs'.",
        stacklevel=2,
    )
    TTS_MODE = "elevenlabs"

# ---------------------------------------------------------------------------
# Twilio
# ---------------------------------------------------------------------------
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

# ---------------------------------------------------------------------------
# Validation — warn at import time if required keys are missing so problems
# surface early rather than at the first API call.
# ---------------------------------------------------------------------------
_REQUIRED = {
    "GROQ_API_KEY": GROQ_API_KEY,
}

if TTS_MODE == "elevenlabs":
    _REQUIRED["ELEVENLABS_API_KEY"] = ELEVENLABS_API_KEY

_twilio_values = {
    "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
    "TWILIO_PHONE_NUMBER": TWILIO_PHONE_NUMBER,
}
if any(_twilio_values.values()):
    _REQUIRED.update(_twilio_values)

_missing = [name for name, value in _REQUIRED.items() if not value]
if _missing:
    warnings.warn(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Set them in your .env file or in the shell environment.",
        stacklevel=2,
    )