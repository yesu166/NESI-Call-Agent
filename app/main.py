import os
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "NESI Call Agent")
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
N8N_SUMMARY_WEBHOOK_URL = os.getenv("N8N_SUMMARY_WEBHOOK_URL", "").strip()

app = FastAPI(title=APP_NAME, version="0.1.0")


class ChatRequest(BaseModel):
    mode: Literal["owner", "caller"] = "caller"
    message: str = Field(min_length=1, max_length=5000)
    language: str = Field(default="English", max_length=40)
    caller_name: Optional[str] = Field(default=None, max_length=120)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)


class SummaryRequest(BaseModel):
    caller_name: str = Field(default="Unknown caller", max_length=120)
    caller_number: Optional[str] = Field(default=None, max_length=40)
    language: str = Field(default="Unknown", max_length=40)
    reason: str = Field(min_length=1, max_length=3000)
    urgency: Literal["normal", "urgent"] = "normal"


def system_prompt(mode: str, language: str, caller_name: Optional[str]) -> str:
    if mode == "owner":
        return f"""
You are NESI, Yesu's personal AI assistant. You are speaking directly to Yesu.
Preferred language: {language}. Talk casually like a close friend: relaxed, warm, a little playful.
Use "bro", "dude", or casual Tanglish naturally when it fits, but don't force slang into every sentence.
Be honest and concise. Never invent calls, messages, plans, caller details, or promises.
This is OWNER MODE. Do not use the formal caller-facing script.
""".strip()
    return f"""
You are NESI, Yesu's AI personal assistant speaking with an external caller.
Caller name if known: {caller_name or "not provided"}.
Respond in {language}, and adapt to the caller's language when possible. Be warm, clear, patient, and respectful.
On a real call, clearly identify yourself as an AI assistant.
Never pretend to be Yesu or a human. Do not claim a message was delivered or a call was transferred unless confirmed.
Ask who is calling and why only when needed. Offer to take a concise message.
Do not use "bro", "dude", "da", teasing, flirting, or owner-mode slang with external callers.
Never invent Yesu's location, availability, schedule, opinions, or commitments.
Keep each response short enough to sound natural on a phone call.
""".strip()


async def ollama_chat(mode: str, message: str, language: str, caller_name: Optional[str]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt(mode, language, caller_name)},
            {"role": "user", "content": message},
        ],
        "options": {"temperature": 0.65, "num_predict": 220},
    }
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "").strip()


def fallback_reply(req: ChatRequest) -> str:
    if req.mode == "owner":
        return (
            f"Bro, I got you. You said: {req.message}. "
            "I can help you work through it, but I won't make up details I don't know."
        )
    greeting = f"{req.caller_name}, " if req.caller_name else ""
    return (
        f"Hello, {greeting}I'm NESI, Yesu's AI personal assistant. "
        "He's unavailable to take the call right now. Could you briefly tell me what this is regarding? "
        "I'll prepare a message for him."
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ollama_enabled": OLLAMA_ENABLED,
        "elevenlabs_configured": bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
        "n8n_configured": bool(N8N_SUMMARY_WEBHOOK_URL),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if OLLAMA_ENABLED:
        try:
            answer = await ollama_chat(req.mode, req.message, req.language, req.caller_name)
            if answer:
                return {"mode": req.mode, "language": req.language, "reply": answer, "provider": "ollama"}
        except (httpx.HTTPError, ValueError, KeyError):
            pass
    return {"mode": req.mode, "language": req.language, "reply": fallback_reply(req), "provider": "fallback"}


@app.post("/speak")
async def speak(req: SpeakRequest):
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=503, detail="Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env first.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "accept": "audio/mpeg", "content-type": "application/json"}
    payload = {
        "text": req.text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.25, "use_speaker_boost": True},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            upstream = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Could not reach ElevenLabs.") from exc
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="ElevenLabs rejected the request. Check the key, voice ID, and quota.")
    return Response(content=upstream.content, media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="nesi.mp3"'})


@app.post("/summary")
async def send_summary(req: SummaryRequest):
    payload = req.model_dump()
    if not N8N_SUMMARY_WEBHOOK_URL:
        return {"sent": False, "reason": "N8N_SUMMARY_WEBHOOK_URL is not configured", "summary": payload}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            result = await client.post(N8N_SUMMARY_WEBHOOK_URL, json=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Could not reach n8n.") from exc
    if result.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"n8n returned HTTP {result.status_code}")
    return {"sent": True, "n8n_status": result.status_code}
