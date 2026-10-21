# NESI Call Agent

NESI is a Gemini-first personal voice assistant prototype for Yesu. The first milestone is a local browser voice session with live audio, multilingual conversation, and interruption support. It is **not yet connected to a real phone number**.

## Current architecture

- **Gemini Live API:** real-time speech-to-speech, server-side session, audio streaming, and model-side turn detection.
- **FastAPI:** keeps the Gemini API key on the server and proxies audio between the browser and Gemini.
- **Browser UI:** captures microphone audio, sends mono PCM at 16 kHz, plays Gemini's 24 kHz PCM output, and clears queued playback on interruption events.
- **Gemini text API:** backs the simple `POST /chat` endpoint.
- **Optional Ollama:** local fallback for text chat only.
- **n8n:** optional post-call summary webhook. It is not part of the live audio loop.
- **Telephony:** not implemented yet. Airtel/Jio SIM forwarding requires a separate supported inbound call/SIP route and may incur charges.

## Quick start (Windows)

Requires Python 3.10+ and a microphone. Use headphones for better echo control.

```powershell
git clone https://github.com/yesu166/NESI-Call-Agent.git
cd NESI-Call-Agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

1. Create a Gemini API key at https://aistudio.google.com/apikey.
2. Put it in `.env` as `GEMINI_API_KEY=...`. Do not commit this file.
3. Start the server:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

4. Open http://127.0.0.1:8000 and allow microphone access.
5. Choose **Owner** to talk privately to NESI, or **Caller** to test the external-caller persona. Test English, Tamil, and Tanglish.
6. Interrupt NESI while she is speaking to test barge-in.

The Gemini Live model defaults to `gemini-3.8-live` and the text endpoint defaults to `gemini-2.5-flash`. If your AI Studio project does not have access to the configured Live model, set `GEMINI_LIVE_MODEL` to a Live API model available to your account. Current model names and access can change; see https://ai.google.dev/gemini-api/docs/models.

## API endpoints

- `GET /`: local voice interface.
- `GET /health`: configuration status, never returns the API key.
- `POST /chat`: text-only test endpoint.
- `WS /ws/live?mode=owner&language=English`: browser-to-Gemini live audio bridge. Caller mode also accepts `caller_name`.
- `POST /summary`: sends a validated summary payload to `N8N_SUMMARY_WEBHOOK_URL`, if configured.

Example text request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"mode":"owner","language":"English","message":"Help me plan my day"}'
```

## What is implemented

- Gemini Live WebSocket session with native audio output.
- Browser microphone capture and PCM audio conversion.
- Live audio playback and transcript display.
- Interruption event handling to stop queued playback.
- Owner and external-caller prompts.
- Text chat endpoint, health endpoint, optional Ollama text fallback, optional n8n summary POST.

## Not implemented yet

- Incoming or outgoing PSTN phone calls.
- Airtel/Jio call forwarding, Indian phone number provisioning, or SIP bridge.
- Persistent call history or automatic post-call transcript summarization.
- Production authentication, rate limiting, and deployment hardening.
- Automated integration tests against a real Gemini Live session.

## Important security and cost notes

- The API key stays in the backend `.env`; never place it in browser JavaScript or commit it.
- This starter binds to localhost by default. **Do not expose the app publicly as-is**: the WebSocket endpoint has no user authentication or rate limiting yet.
- Free API quotas, model availability, and data-use terms depend on Google's current AI Studio/Gemini API policies. Check them before sending sensitive caller information.
- The local browser prototype is not an answer-to-SIM feature. Do not enable call forwarding until a compatible destination is verified and end-to-end tested.
- NESI identifies itself as an AI assistant and must not impersonate Yesu or disclose private information.
