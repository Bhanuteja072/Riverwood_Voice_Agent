# Riverwood Voice Agent

An AI-powered voice agent named **Riya** for Riverwood Projects LLP. Riya calls customers, shares construction progress updates for Riverwood Estate (Sector 7, Kharkhauda), and holds a natural Hinglish conversation — all from the browser.

Built as part of the Riverwood AI Systems Internship Challenge.

---

## What It Does

- Greets customers by name in natural Hinglish
- Shares live construction progress updates for Riverwood Estate
- Accepts voice input (mic) or text input
- Replies in natural speech using ElevenLabs (with gTTS fallback)
- Remembers full conversation context across the entire call
- Switches to English automatically when customer speaks English

---

## Tech Stack

| Component | Tool |
|-----------|------|
| LLM (Brain) | Groq Llama 3.3 70B |
| Speech to Text | Local OpenAI Whisper (base model) |
| Text to Speech | ElevenLabs `eleven_multilingual_v2` + gTTS fallback |
| Backend | FastAPI (Python) |
| Language Detection | langdetect |
| Frontend | Vanilla HTML/JS (browser UI) |

---

## Requirements

- Python 3.10+
- FFmpeg installed and available in PATH (required by Whisper)

Install FFmpeg:
- **Windows:** Download from https://ffmpeg.org/download.html and add to PATH
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

---

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/riverwood-voice-agent
   cd riverwood-voice-agent
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   GROQ_API_KEY=your_groq_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_key_here
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
   TTS_MODE=elevenlabs
   ```

4. Run the server:
   ```
   python -m uvicorn backend.main:app --reload
   ```

5. Open your browser at:
   ```
   http://127.0.0.1:8000
   ```

---

## Getting Free API Keys

| Key | Where to Get |
|-----|-------------|
| `GROQ_API_KEY` | console.groq.com — free, no credit card needed |
| `ELEVENLABS_API_KEY` | elevenlabs.io — free tier (10,000 chars/month) |

---

## TTS Modes

| Mode | Quality | Cost |
|------|---------|------|
| `TTS_MODE=elevenlabs` | Natural, human-like voice | Free tier available |
| `TTS_MODE=gtts` | Basic Google TTS | Completely free |

If `TTS_MODE=elevenlabs` and the ElevenLabs API fails or quota runs out, the app automatically falls back to gTTS.

---

## Project Structure

```
riverwood-voice-agent/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── agent.py         # Groq LLM + conversation memory
│   ├── voice_in.py      # Whisper speech-to-text
│   ├── voice_out.py     # ElevenLabs + gTTS text-to-speech
│   ├── prompts.py       # Riya's personality + construction data
│   ├── config.py        # Environment variables
│   └── call_manager.py  # Twilio outbound call management
│   └── twilio_handler.py  # TwiML response builder
├── frontend/
│   └── index.html       # Browser UI
├── .env                 # API keys (do not commit)
├── requirements.txt
├── README.md
└── technical_note.md
```

---

## Notes

- Twilio integration is fully implemented — call_manager.py places outbound calls, twilio_handler.py builds TwiML responses
- For production, replace in-memory sessions with Redis
- Whisper base model runs locally — no OpenAI API key needed for STT