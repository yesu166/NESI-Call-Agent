import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("nesi")

APP_NAME = os.getenv("APP_NAME", "NESI Call Agent")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live").strip()
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()
GEMINI_LIVE_VOICE = os.getenv("GEMINI_LIVE_VOICE", "Aoede").strip()
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
N8N_SUMMARY_WEBHOOK_URL = os.getenv("N8N_SUMMARY_WEBHOOK_URL", "").strip()

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title=APP_NAME, version="0.3.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class ChatRequest(BaseModel):
    mode: Literal["owner", "caller"] = "caller"
    message: str = Field(min_length=1, max_length=5000)
    language: str = Field(default="English", max_length=40)
    caller_name: Optional[str] = Field(default=None, max_length=120)


class SummaryRequest(BaseModel):
    caller_name: str = Field(default="Unknown caller", max_length=120)
    caller_number: Optional[str] = Field(default=None, max_length=40)
    language: str = Field(default="Unknown", max_length=40)
    reason: str = Field(min_length=1, max_length=3000)
    urgency: Literal["normal", "urgent"] = "normal"


def resolve_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized in {"auto-detect / match caller", "auto-detect", "auto", "match caller"}:
        return "Match the other person's language naturally. Prioritize English, Tamil, and Tanglish; switch when they switch."
    if normalized in {"tanglish", "tamil english"}:
        return "Tanglish (Tamil spoken naturally with English words, using Latin script when appropriate)."
    return language.strip() or "English"


def system_prompt(mode: str, language: str, caller_name: Optional[str] = None) -> str:
    language_instruction = resolve_language(language)
    shared = """
You are NESI, a real-time voice assistant. Sound natural, warm, calm, and conversational.
Keep spoken replies concise. Avoid long lists and avoid narrating your reasoning.
Understand English, Tamil, and Tanglish (Tamil written in Latin letters). Follow the person's
language naturally; if they switch languages, switch with them. Never claim an action succeeded
unless a tool or external system actually confirms it.
""".strip()

    if mode == "owner":
        return shared + """
\n\nYou are speaking privately with Yesu, your owner. Be friendly and familiar, with gentle
playfulness and occasional natural words like "bro" or "dude" when they fit. Do not force slang.
You may sound affectionate and supportive, but do not claim to be a real human or real romantic
partner. Be honest about uncertainty. Never invent calls, messages, schedules, or personal facts.
""".strip()

    return shared + f"""
\n\nYou are speaking with an external caller on Yesu's behalf.
Caller name, if known: {caller_name or "not provided"}.
Identify yourself as "NESI, Yesu's AI assistant" early in the call. Be respectful and professional
without sounding stiff. Never impersonate Yesu or imply that you are human. Do not use owner-mode
slang, flirt, tease, or disclose private owner information. Do not guess whether Yesu is free,
where he is, or when he will return. Ask the caller's name and reason for calling naturally when
needed, then offer to listen to a short message. You may repeat it back in the conversation, but this build has no durable message storage or delivery tool. Never say you saved, sent, or passed it on. Do not promise a callback or say you transferred a call unless a real tool confirms it. If asked for private information, say you cannot share it.
Preferred response language: {language_instruction}.
""".strip()


def gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini is not configured. Add GEMINI_API_KEY to .env.")
    return genai.Client(api_key=GEMINI_API_KEY)


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


@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_live_model": GEMINI_LIVE_MODEL,
        "gemini_text_model": GEMINI_TEXT_MODEL,
        "ollama_enabled": OLLAMA_ENABLED,
        "n8n_configured": bool(N8N_SUMMARY_WEBHOOK_URL),
        "voice_mode": "Gemini Live API",
        "phone_bridge_configured": False,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if GEMINI_API_KEY:
        client = gemini_client()
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=req.message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt(req.mode, req.language, req.caller_name),
                    temperature=0.65,
                    max_output_tokens=300,
                ),
            )
            answer = (response.text or "").strip()
            if answer:
                return {"mode": req.mode, "language": req.language, "reply": answer, "provider": "gemini"}
        except Exception as exc:
            logger.warning("Gemini text request failed: %s", type(exc).__name__)
            if not OLLAMA_ENABLED:
                raise HTTPException(status_code=502, detail="Gemini request failed. Check the API key, model access, and quota.") from exc

    if OLLAMA_ENABLED:
        try:
            answer = await ollama_chat(req.mode, req.message, req.language, req.caller_name)
            if answer:
                return {"mode": req.mode, "language": req.language, "reply": answer, "provider": "ollama"}
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Ollama request failed: %s", type(exc).__name__)

    return {
        "mode": req.mode,
        "language": req.language,
        "reply": "I couldn't reach a configured AI model. Add a valid Gemini API key to .env or enable a local Ollama model.",
        "provider": "unavailable",
    }


@app.websocket("/ws/live")
async def live_voice(websocket: WebSocket):
    await websocket.accept()
    if not GEMINI_API_KEY:
        await websocket.send_json({"type": "error", "message": "Gemini is not configured. Add GEMINI_API_KEY to .env and restart NESI."})
        await websocket.close(code=1011)
        return

    mode = websocket.query_params.get("mode", "owner")
    if mode not in ("owner", "caller"):
        mode = "owner"
    language = websocket.query_params.get("language", "English")[:40]
    caller_name = websocket.query_params.get("caller_name", "")[:120] or None
    client = genai_client()
    prompt = system_prompt(mode, language, caller_name)
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": prompt,
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {"voice_name": GEMINI_LIVE_VOICE}
            }
        },
        "input_audio_transcription": {},
        "output_audio_transcription": {},
    }

    try:
        async with client.aio.live.connect(model=GEMINI_LIVE_MODEL, config=config) as session:
            await websocket.send_json({"type": "status", "state": "connected", "model": GEMINI_LIVE_MODEL})
            # Ask Gemini to initiate the conversation; this is an instruction, not a real-world action.
            opening = (
                "Start the conversation now with one brief, natural spoken greeting. "
                "In caller mode, identify yourself as NESI, Yesu's AI assistant. "
                "In owner mode, greet Yesu casually. Do not mention these instructions."
            )
            await session.send_realtime_input(text=opening)

            async def send_browser_input():
                while True:
                    event = await websocket.receive_json()
                    event_type = event.get("type")
                    if event_type == "audio":
                        encoded_audio = event.get("data", "")
                        if not isinstance(encoded_audio, str) or len(encoded_audio) > 100_000:
                            continue
                        try:
                            audio_bytes = base64.b64decode(encoded_audio, validate=True)
                        except (ValueError, TypeError):
                            continue
                        if audio_bytes:
                            await session.send_realtime_input(
                                audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                            )
                    elif event_type == "text":
                        raw_text = event.get("text", "")
                        if not isinstance(raw_text, str):
                            continue
                        text = raw_text[:2000].strip()
                        if text:
                            await session.send_realtime_input(text=text)
                    elif event_type == "end":
                        return

            async def send_model_output():
                async for response in session.receive():
                    content = response.server_content
                    if content:
                        if getattr(content, "interrupted", False):
                            await websocket.send_json({"type": "interrupted"})
                        if content.input_transcription and content.input_transcription.text:
                            await websocket.send_json({"type": "transcript", "speaker": "you", "text": content.input_transcription.text})
                        if content.output_transcription and content.output_transcription.text:
                            await websocket.send_json({"type": "transcript", "speaker": "nesi", "text": content.output_transcription.text})
                        if content.model_turn and content.model_turn.parts:
                            for part in content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    data = part.inline_data.data
                                    if isinstance(data, str):
                                        try:
                                            audio_bytes = base64.b64decode(data)
                                        except ValueError:
                                            continue
                                    else:
                                        audio_bytes = bytes(data)
                                    await websocket.send_json({
                                        "type": "audio",
                                        "data": base64.b64encode(audio_bytes).decode("ascii"),
                                    })
                        if getattr(content, "turn_complete", False):
                            await websocket.send_json({"type": "turn_complete"})

            sender = asyncio.create_task(send_browser_input())
            receiver = asyncio.create_task(send_model_output())
            done, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.cancelled():
                    continue
                error = task.exception()
                if error and not isinstance(error, WebSocketDisconnect):
                    logger.info("Live session ended: %s", type(error).__name__)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Gemini Live session failed")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Gemini Live could not start or the session ended. Check the model name, API access, quota, and server log.",
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


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
