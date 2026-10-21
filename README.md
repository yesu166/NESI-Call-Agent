# NESI Call Agent

NESI is Yesu's multilingual personal AI call assistant. The intended experience is warm and conversational with callers, casual only in private owner notifications, and interruptible so a caller can speak over the agent and continue naturally.

## Recommended architecture

- **ElevenLabs Conversational AI (ElevenAgents):** real-time voice, speech recognition/synthesis, multilingual conversation, turn-taking, and interruption handling.
- **n8n self-hosted:** asynchronous post-call summaries, notifications, and approved automation. Do not route every audio turn through n8n.
- **Python/FastAPI:** optional custom tools and secure application endpoints.
- **Telephony provider / SIP:** connects the agent to real telephone calls. This is a separate component and may cost money.

## Free-tier reality

ElevenLabs currently lists 15 minutes of calls on its Agents Free plan; check your current account limits before relying on this. Telephone number rental and PSTN call charges are separate. Native Twilio integration requires a Twilio account and active number, and ElevenLabs documents direct SIP trunking as Enterprise-only. Therefore, first test through the ElevenLabs web preview/widget; do not assume calls to your existing Airtel SIM can be answered for free.

## Setup guide

Follow [docs/VOICE_AGENT_SETUP.md](docs/VOICE_AGENT_SETUP.md). Paste [docs/agent-prompt.md](docs/agent-prompt.md) into your ElevenLabs agent instructions. Enable interruptions in the agent's conversation-flow settings and test English, Tamil, and Tanglish before adding phone routing.

## n8n workflows

- [ElevenLabs post-call webhook workflow](n8n/elevenlabs-post-call-workflow.json): receives a post-call event and normalizes transcript/summary data. It is a prototype and does not verify webhook signatures or send Telegram/email yet.
- [Basic summary workflow](n8n/nesi-call-summary-workflow.json): starter webhook for manually submitted call summaries.

For a live webhook, n8n must be reachable over HTTPS; an external service cannot call localhost. Secure the endpoint and verify ElevenLabs' HMAC signature before using real caller data.

## Existing local API prototype

The repository also contains a Python/FastAPI API with `/health`, `/chat`, `/speak`, and `/summary`, optional Ollama chat, and optional ElevenLabs TTS. This API is a local prototype, **not yet the live telephone audio bridge**.

Windows setup:

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

Open http://127.0.0.1:8000/docs.

## Not implemented yet

- Live inbound/outbound phone calls
- Airtel forwarding or SIP/PSTN routing
- A real-time custom audio bridge
- Persistent call history
- Telegram/email notifications wired to credentials
- Production webhook signature verification

## Privacy and safety

- Identify NESI as an AI assistant to callers.
- Never commit API keys or `.env`.
- Collect only necessary caller data and configure retention/consent deliberately.
- Do not configure Airtel call forwarding until the destination and end-to-end test are confirmed.
- Use an approved knowledge base/tools for Yesu-specific facts. The LLM must not invent personal details or claim actions were completed without confirmation.
