# NESI Call Agent | Project Brief

> **Proposed repository description:** A local browser-based multilingual voice-assistant prototype using Gemini Live, FastAPI, WebSockets, and optional Ollama and n8n integrations.

## Overview
NESI Call Agent is a voice-first assistant prototype built around browser microphone input and the Gemini Live API. It explores responsive spoken conversation, interruption handling, language matching, and a small backend integration surface.

## Problem and opportunity
Voice interfaces require more than text responses played through a speaker. They need low-latency streaming, natural turn-taking, interruption handling, clear session state, and accurate reporting when a model or network connection is unavailable.

## Proposed approach
- Stream microphone audio from the local browser through a FastAPI WebSocket to Gemini Live.
- Play returned audio and show transcriptions when available.
- Support separate Owner and Caller conversation modes and language options, including English, Tamil, and Tanglish.
- Keep provider credentials in the Python process rather than browser code.
- Treat Ollama text fallback and n8n summary forwarding as optional integrations, not mandatory runtime requirements.

## Current scope and maturity
The README describes a local browser voice prototype. It explicitly states that inbound/outbound phone calls, SIP/PSTN routing, SIM call forwarding, persistent call history, and automatic post-call summaries are not implemented. It also notes missing authentication/rate limiting and lack of CI testing against a real Gemini Live session.

## Roadmap proposal
1. Add and test explicit session lifecycle management, interruption, reconnection, and cancellation.
2. Add automated tests for malformed audio, model unavailability, WebSocket closure, and transcript handling.
3. Add authentication, rate limiting, origin validation, and safe deployment configuration before any non-local exposure.
4. Add reliable consent-aware transcript and summary handling, including retention controls.
5. Select a compatible telephony provider and implement phone-call routing as a separate milestone with dedicated tests.
6. Run end-to-end tests against the chosen provider and document costs, limitations, and failure handling.

## Safety and privacy boundaries
Voice data, transcripts, and call summaries may contain sensitive information. Make recording and retention behaviour explicit, minimize data collection, avoid logging secrets, and obtain the required consent before recording or forwarding content. Do not expose the local development server publicly until access controls and session protections are hardened.

## Collaboration proposal
Useful contributions include WebSocket lifecycle tests, interruption and latency measurements, Tamil/Tanglish usability, secure configuration, privacy documentation, and reproducible setup instructions. Telephony must remain labelled as planned until real call flows are tested.

## Licensing and reuse
The root license, if present, governs reuse of this repository. This brief does not grant additional rights. Review the Gemini API, SDK, Ollama, and n8n terms separately before redistributing integrations or packaged deployments.
