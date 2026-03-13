# Riverwood Voice Agent — Technical Note

Submission for the Riverwood Projects LLP AI Systems Internship Challenge.

---

## System Architecture

```
[Browser UI]
     |
     | Voice (WebM) or Text
     v
[FastAPI Backend]
     |
     |-- Whisper (local) --> Transcribed Text
     |-- Groq Llama 3.3 70B --> Agent Reply Text
     |-- ElevenLabs / gTTS --> MP3 Audio
     |
     v
[Browser plays audio + shows transcript]
```

### Components

**LLM — Groq Llama 3.3 70B**
Handles all conversation logic. Full conversation history is passed on every turn, giving Riya complete memory of the call. Temperature set to 0.8 for natural, warm responses.

**Speech to Text — Local OpenAI Whisper (base)**
Runs entirely on the local machine. No API call needed. Accepts WebM audio from the browser mic, transcribes in Hindi/English. FFmpeg required for audio decoding.

**Text to Speech — ElevenLabs + gTTS fallback**
ElevenLabs `eleven_multilingual_v2` model produces natural Hindi/English voice. If ElevenLabs fails or quota runs out, gTTS takes over automatically with no interruption.

**Language Detection — langdetect**
Detects if the customer speaks in English. If English is detected, a system instruction is injected into the LLM context forcing English-only replies. Fails silently if detection is uncertain.

**Session Memory**
Each call gets a unique session ID (UUID4). Full conversation history stored in memory per session. Riya remembers everything said in the call — construction updates, customer preferences, visit plans.

**Frontend**
Single HTML file. Mic button records WebM audio and sends to `/respond-voice`. Text box sends to `/respond-text`. MP3 audio auto-plays. Chat transcript displays both sides of the conversation.

---

## Conversation Flow (Example Scenario)

```
1. Customer enters name → clicks Start Call
2. Riya greets by name in Hinglish
3. Customer says "haan bolo" → Riya shares construction update
4. Riya asks if customer plans to visit the site
5. Customer responds → Riya handles gracefully (schedules or acknowledges)
6. Customer asks questions → Riya answers from project knowledge
7. Customer ends call → Riya wraps up warmly
```

---

## Evaluation Criteria Mapping

| Criteria | Weight | How This Prototype Addresses It |
|----------|--------|--------------------------------|
| Voice Realism | 25% | ElevenLabs eleven_multilingual_v2 — natural Hinglish voice |
| Latency | 20% | Groq is fastest available LLM API. Local Whisper avoids STT API latency. gTTS as instant fallback |
| Infrastructure Design | 20% | See scaling section below |
| Context Understanding | 20% | Full conversation history passed to LLM every turn. Customer name injected into system prompt |
| Creativity | 15% | Riya has a warm personality, uses customer name, speaks natural Hinglish, handles voicemail and callbacks |

---

## Scaling to 1000 Calls Per Morning

### Problem
1000 customers need to receive a personalised call every morning. Each call is ~3-4 minutes. All calls should ideally complete within a 2-hour window (7AM–9AM).

### Proposed Infrastructure

**Step 1 — Outbound Calling**
Replace the browser UI with VAPI or Twilio Programmable Voice. Each customer record triggers an outbound call. `call_manager.py` is already structured for this integration.

**Step 2 — Call Queuing**
Use AWS SQS or Redis Queue. Load all 1000 customer records at 6:55 AM. Fire calls in batches of 50 per minute to avoid Twilio rate limits. Each queue item contains customer name, phone number, and personalised construction update.

**Step 3 — Auto-scaling Backend**
Deploy FastAPI on AWS Lambda or Google Cloud Run. These scale automatically — if 200 calls are active simultaneously, 200 instances spin up. No manual scaling needed.

**Step 4 — Session Storage**
Replace in-memory dict with Redis. Each call session stored as a Redis key with 1-hour TTL. Handles concurrent sessions across multiple backend instances.

**Step 5 — Conversation Logging**
Store full conversation transcript per call in PostgreSQL or DynamoDB. Linked to customer CRM record. Enables Riverwood team to review calls, flag follow-ups, and track sentiment.

### Architecture Diagram

```
6:55 AM — Customer DB
     |
     v
AWS SQS Queue (1000 jobs)
     |
     | 50 calls/min
     v
VAPI / Twilio  ←→  Cloud Run (FastAPI) ←→ Redis Sessions
                        |
                   Groq LLM API
                   ElevenLabs TTS
                        |
                   PostgreSQL (logs)
```

### Estimated Cost for 1000 Calls Per Day

| Service | Calculation | Cost/Day |
|---------|-------------|----------|
| Groq LLM (Llama 3.3 70B) | Free tier — $0 for prototype scale | ~$0 |
| ElevenLabs TTS | ~500 chars/call × 1000 = 500k chars @ $0.30/1k chars | ~$150 |
| Local Whisper → Cloud Whisper | $0.006/min × 3 min × 1000 calls | ~$18 |
| VAPI outbound calls | ~$0.05/min × 3 min × 1000 | ~$150 |
| Cloud Run / Lambda | ~$0.00001/request × 1000 | ~$0.01 |
| Redis (session storage) | Negligible at this scale | ~$1 |
| **Total** | | **~₹27,000/day (~$320/day)** |

> Cost can be reduced significantly by using gTTS instead of ElevenLabs (saves ~$150/day) and batching calls to lower-cost hours.

---

## Production Deployment Path

```
Prototype (current)     →  Browser UI, local Whisper, gTTS/ElevenLabs, in-memory sessions
Stage 2 (with keys)     →  Add Twilio/VAPI for real outbound calls
Stage 3 (production)    →  Cloud Run + Redis + PostgreSQL + ElevenLabs streaming
```

---

## Repository
GitHub: https://github.com/Bhanuteja072/Riverwood_Voice_Agent