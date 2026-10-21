# NESI

**My personal AI voice agent, built around Gemini Live.**

NESI is an experiment in making voice-first AI feel immediate and useful: low-latency conversation, natural turn-taking, multilingual speech, and a distinct personality depending on who is speaking.

The current milestone is a **local browser voice prototype**. Phone-call routing is a separate piece of work and is not implemented yet.

## What it does today

- Streams microphone audio to the Gemini Live API and plays back generated speech.
- Supports separate **Owner** and **Caller** conversation modes.
- Includes English, Tamil, Tanglish, and language-matching options.
- Displays input/output transcriptions when Gemini provides them.
- Stops queued playback when Gemini reports an interruption.
- Exposes a small FastAPI text endpoint, with optional Ollama fallback.
- Can forward a manually supplied call-summary payload to an n8n webhook.

## Stack

| Layer | Technology |
| --- | --- |
| Live voice | Gemini Live API, Google GenAI Python SDK |
| Backend | Python, FastAPI, WebSockets |
| Interface | HTML, CSS, vanilla JavaScript, Web Audio API |
| Optional local text model | Ollama |
| Automation hook | n8n |

## Architecture

```text
Browser microphone
      │  PCM16, 16 kHz
      ▼
FastAPI WebSocket ─────► Gemini Live API
      ▲                       │
      └──── PCM audio ◄───────┘
      │
      └── Local transcript + playback UI

FastAPI /summary ─────► Optional n8n webhook
```

The Gemini API key stays in the Python process. The browser only talks to the local FastAPI server.

## Run locally

Python 3.10+ is required. A microphone and a Gemini API key with Live API access are needed for voice sessions.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`, then run:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Headphones are recommended to reduce microphone feedback.

The Live model is configurable with `GEMINI_LIVE_MODEL`; model availability depends on the Google AI project. Reference: [Gemini Live API](https://ai.google.dev/gemini-api/docs/live-api).

## API surface

- `GET /` · local interface
- `GET /health` · configuration status
- `POST /chat` · text-only conversation
- `WS /ws/live` · live audio/text session
- `POST /summary` · optional n8n summary webhook

## Current boundaries

- No inbound/outbound phone calls, SIP, PSTN, or SIM call forwarding.
- No persistent call history or automatic post-call transcription summary.
- No authentication or rate limiting on the local WebSocket endpoint.
- No end-to-end test against a real Gemini Live session in CI.

This is an active prototype, not a production call-answering service. The app binds to localhost by default; it should not be exposed publicly until authentication, rate limiting, origin validation, and session lifecycle handling are hardened.

## Direction

1. Stabilize live audio, interruption, and transcript behavior.
2. Add deliberate session lifecycle and message-summary handling.
3. Choose and test a compatible telephony/SIP provider.
4. Add call history and explicit, consent-aware notification actions.
