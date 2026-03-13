import os
import tempfile
import whisper

_MODEL_NAME = "base"
_MODEL = whisper.load_model(_MODEL_NAME)


def speech_to_text(audio_bytes: bytes) -> str:
    """Convert audio bytes to text using local Whisper.

    Args:
        audio_bytes: Raw audio data to transcribe.
    Returns:
        Transcribed text string (empty string if audio contained no speech).

    Raises:
        ValueError: if *audio_bytes* is empty.
        RuntimeError: if the Whisper API call fails.
    """
    if not audio_bytes:
        raise ValueError("speech_to_text: audio_bytes must not be empty.")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = _MODEL.transcribe(tmp_path, language="hi")
        except Exception as exc:
            raise RuntimeError(f"Speech-to-text call failed: {exc}") from exc

        return (result.get("text") or "").strip()

    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass  # already removed — nothing to do