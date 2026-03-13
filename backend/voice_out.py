import io

import requests
from gtts import gTTS

from .config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, TTS_MODE

# Seconds to wait for ElevenLabs to respond; keeps calls from hanging.
_REQUEST_TIMEOUT = 15


def text_to_speech_elevenlabs(text: str) -> bytes:
    """Convert text to speech using ElevenLabs. Returns raw MP3 bytes.

    Raises:
        ValueError: if *text* is empty or the API returns no audio data.
        requests.HTTPError: if the ElevenLabs API returns a non-2xx status,
            with the response body included in the error message.
        requests.Timeout: if the API does not respond within _REQUEST_TIMEOUT seconds.
    """
    if not text or not text.strip():
        raise ValueError("text_to_speech_elevenlabs: text must not be empty.")

    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is missing. Set it in your environment.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.4,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT)

    if not response.ok:
        # Include ElevenLabs error body so callers know the real reason
        raise requests.HTTPError(
            f"ElevenLabs API error {response.status_code}: {response.text}",
            response=response,
        )

    audio_bytes = response.content
    if not audio_bytes:
        raise ValueError("ElevenLabs returned an empty audio response.")

    return audio_bytes  # MP3 bytes


def text_to_speech_gtts(text: str) -> bytes:
    """Convert text to speech using gTTS. Returns raw MP3 bytes."""
    if not text or not text.strip():
        raise ValueError("text_to_speech_gtts: text must not be empty.")

    mp3_buffer = io.BytesIO()
    tts = gTTS(text=text, lang="hi")
    tts.write_to_fp(mp3_buffer)
    return mp3_buffer.getvalue()


def text_to_speech(text: str) -> bytes:
    """Convert text to speech using ElevenLabs with gTTS fallback."""
    print(f"TTS_MODE={TTS_MODE}, using elevenlabs first")
    if TTS_MODE == "gtts":
        return text_to_speech_gtts(text)

    try:
        return text_to_speech_elevenlabs(text)
    except Exception:
        return text_to_speech_gtts(text)