# Architecture & engineering notes

NESI is being built as a voice-first personal assistant. The current implementation deliberately separates browser audio, model inference, automation, and future telephony.

## Live conversation path

1. The browser captures mono audio and converts it to signed 16-bit PCM.
2. The browser sends audio frames over a same-origin WebSocket to FastAPI.
3. FastAPI streams frames to Gemini Live using the Google GenAI SDK.
4. Gemini audio chunks are relayed to the browser for 24 kHz playback.
5. Input/output transcriptions are shown when the Live API returns them.

The browser is a local development client. It is not a SIP endpoint and does not connect to a mobile SIM.

## Conversation modes

- **Owner:** familiar, relaxed voice for private interaction with Yesu.
- **Caller:** identifies NESI as an AI assistant, avoids disclosing private information, and can offer to take a message. Message persistence and callback tools are not implemented.

The mode-specific instructions are currently built in `app/main.py`. `docs/agent-prompt.md` describes the intended behavior and should stay aligned with the code.

## Current implementation

| Component | Status |
| --- | --- |
| Gemini Live audio bridge | Implemented; needs real-account end-to-end testing |
| Browser voice UI | Implemented; audio UX still needs refinement |
| Input/output transcript display | Implemented where transcription events are returned |
| Text chat endpoint | Implemented |
| Ollama text fallback | Optional |
| n8n summary webhook | Manual payload forwarding only |
| Call history and message storage | Not implemented |
| SIP/PSTN/Indian mobile call forwarding | Not implemented |
| Public deployment hardening | Not implemented |

## Important behavior and constraints

- Gemini Live audio input is raw PCM16 at 16 kHz; generated audio is PCM at 24 kHz.
- Live API model access and quotas depend on the Google AI project.
- Live sessions have provider-defined duration/context limits; session renewal is not implemented.
- The app binds to localhost by default. The WebSocket route does not authenticate users and must not be exposed publicly as-is.
- No callback, message, or transfer should be promised until a real integration records or confirms it.
- The summary endpoint accepts caller-supplied structured data. It does not derive a summary from the live transcript.

## Next engineering priorities

1. Test the complete live session against a real Gemini project.
2. Improve audio queueing, interruption recovery, reconnection, and transcript turn boundaries.
3. Add deliberate session lifecycle management and optional persistence.
4. Evaluate Indian-compatible inbound telephony and SIP providers before enabling forwarding.
5. Add authentication, rate limiting, origin checks, and privacy controls before any remote deployment.
