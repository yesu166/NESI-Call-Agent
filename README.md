# NESI Call Agent

NESI is Yesu's personal AI call assistant. This repo contains the first runnable API milestone plus optional provider integrations.

## Personality rules

- **Owner mode:** casual, friendly, playful with Yesu.
- **Caller mode:** polite, respectful, and transparent that NESI is an AI assistant.
- Do not use owner-mode slang with callers.
- Start with English; pass `language: "Tamil"` or another language to the chat endpoint when testing multilingual responses.

## Current functionality

- FastAPI endpoints: `/health`, `/chat`, `/speak`, and `/summary`.
- Optional local Ollama chat integration.
- Optional ElevenLabs text-to-speech endpoint.
- Importable n8n call-summary webhook workflow.

**Not implemented yet:** live telephone calls, SIP/Asterisk integration, speech-to-text, streaming/barged-in voice conversations, persistent call history, and actual Telegram/email delivery. Do not configure Airtel call forwarding yet.

## Windows 11 setup

Install Python 3.12 from https://www.python.org/downloads/ then in PowerShell:

```powershell
git clone https://github.com/yesu166/NESI-Call-Agent.git
cd NESI-Call-Agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs and test `POST /chat`.

### Test owner mode

```json
{
  "mode": "owner",
  "message": "I missed a call from Karthik about our college project.",
  "language": "English"
}
```

### Test caller mode

```json
{
  "mode": "caller",
  "message": "Can you tell Yesu to call me back about tomorrow's meeting?",
  "language": "English",
  "caller_name": "Karthik"
}
```

## Optional local LLM

Install Ollama from https://ollama.com, then run:

```powershell
ollama pull qwen3:4b
```

In `.env`:
```dotenv
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Restart the API after changing `.env`.

## Optional ElevenLabs TTS

Create an API key in your ElevenLabs account and put it and a voice ID into the local `.env`:

```dotenv
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
```

Then send `POST /speak` with `{"text":"Hi, I'm NESI, Yesu's AI personal assistant."}`. It returns MP3 audio. Provider quotas and terms apply. Never commit a real key.

## Optional n8n workflow

Run local n8n with `npx n8n`. Open http://localhost:5678 and import `n8n/nesi-call-summary-workflow.json`. Activate it, copy its production webhook URL, and set `N8N_SUMMARY_WEBHOOK_URL` in `.env`. Test `POST /summary`.

The included workflow formats a summary and returns a receipt; it does not yet send Telegram/email messages. Keep n8n local until authentication and secure deployment are configured.

## Security and privacy

- Do not put API keys in source code or GitHub.
- Keep the API bound to localhost for development.
- Clearly identify NESI as an AI assistant on real calls.
- Do not store call recordings or personal details without an appropriate consent and retention policy.
- Only investigate real Airtel call routing after a separate SIP/telephony destination has been tested.
