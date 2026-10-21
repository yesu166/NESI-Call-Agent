# NESI Call Agent

A personal AI call-assistant prototype for Yesu.

## Personality
- **Owner mode:** casual, friendly, playful with Yesu.
- **Caller mode:** respectful, helpful, and transparent that NESI is an AI assistant.
- Multilingual-ready design, starting with English and Tamil/Tanglish.

## Current milestone
This repository is the home for the NESI project. Start with a local API and optional providers, then add speech input/output, n8n notifications, SIP test calls, and finally investigate Airtel call routing.

### Planned stack
- Python + FastAPI for the agent service
- Ollama for optional local LLM inference
- ElevenLabs as an optional hosted text-to-speech provider
- n8n self-hosted for message/notification workflows
- Asterisk/SIP for later telephony testing

## Important
This starter will not answer actual Airtel calls by itself. Do not enable call forwarding until a working, tested telephony destination is configured. Tell callers that NESI is an AI assistant, and obtain appropriate consent before retaining call recordings or personal information.

## Development
The initial API, .env example, and n8n workflow will be added as the next project files. Never commit real API keys or the `.env` file.