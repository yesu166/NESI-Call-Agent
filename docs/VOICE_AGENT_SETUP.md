# NESI voice agent setup

## Decision: Gemini Live first

The first build uses Gemini Live API directly, rather than ElevenLabs or Retell. The goal is to keep the first voice prototype small and avoid adding a separate voice platform before phone routing is solved.

## Stage A: run the local live voice prototype

1. Follow the Windows setup in the repository README.
2. Create an API key at https://aistudio.google.com/apikey and store it in `.env` as `GEMINI_API_KEY`.
3. Start FastAPI on localhost with `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.
4. Open http://127.0.0.1:8000 and allow microphone access.
5. Test Owner mode with English, Tamil, and Tanglish. Test Caller mode separately.
6. Speak while NESI is talking to test interruption behavior. Headphones are recommended to reduce echo.

Official references:
- Gemini Live API: https://ai.google.dev/gemini-api/docs/live-api
- Python SDK quickstart: https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk
- Models and current availability: https://ai.google.dev/gemini-api/docs/models
- Google GenAI Python SDK: https://github.com/googleapis/python-genai

The Live model is configurable through `GEMINI_LIVE_MODEL`. The default is `gemini-3.8-live` according to the current model documentation, but model availability can vary by project and change over time. If connection setup fails, confirm the currently supported Live model in AI Studio/docs before changing application code.

## Stage B: n8n after-call automation

The `POST /summary` endpoint can send a manually supplied summary to `N8N_SUMMARY_WEBHOOK_URL`. This is not yet automatic: the live transcript is not persisted or summarized at session end.

For local testing:
1. Run n8n with `npx n8n`.
2. Open http://localhost:5678.
3. Configure a webhook workflow and put its test URL in `.env`.
4. Restart FastAPI and call `POST /summary` from the API docs.

For a hosted workflow, use HTTPS and authentication. Never expose an unrestricted webhook that can trigger sensitive actions.

## Stage C: connect real phone calls (not implemented)

To answer calls forwarded from an existing Airtel/Jio SIM, NESI needs an inbound telephony route that accepts the forwarded call and streams audio to the agent. The browser WebSocket bridge in this repository does not speak SIP or PSTN.

Before choosing a provider, verify all of the following:
- It supports inbound calls for an Indian number or a lawful compatible SIP destination.
- Your existing carrier permits forwarding to that destination.
- Number rental, inbound minutes, forwarding, and SIP/media charges are clear.
- The provider can bridge full-duplex audio with acceptable latency.
- You can identify the AI to callers and handle personal data appropriately.

Do not assume a US free number, a SIP demo, or a free Gemini API key makes Indian PSTN calls free. Keep call forwarding disabled until an end-to-end test succeeds.

## Safety and deployment limits

- Keep `.env` out of Git.
- The current local WebSocket endpoint does not authenticate users. Bind to `127.0.0.1` only; do not deploy it publicly without authentication, rate limiting, origin checks, and abuse controls.
- Do not send sensitive caller data through free-tier APIs until you have reviewed the current data-use terms.
- Caller mode must identify NESI as an AI assistant, must not impersonate Yesu, and must not invent Yesu's schedule, location, or commitments.
- Ask for confirmation before any future tool sends a message, makes a booking, or takes another consequential action.
