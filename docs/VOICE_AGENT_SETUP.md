# NESI voice agent setup

## Architecture decision

Use **ElevenLabs Conversational AI (ElevenAgents)** as the real-time voice runtime for the first milestone. It handles speech input/output, turn-taking, multilingual conversations, and interruption events. Do not route each spoken turn through n8n; that adds latency and makes barge-in harder.

Use **n8n for asynchronous automation**: post-call transcript processing, summary creation, Telegram/email notification, and optionally approved lookups/actions exposed as authenticated webhook tools.

## Reality check: free tier vs free phone calls

- ElevenAgents currently lists a Free plan with 15 minutes of calls. Confirm your account's live plan page before relying on this.
- ElevenLabs call minutes and telephony-provider charges are separate. A Twilio phone number and PSTN usage require a paid Twilio account/number.
- Connecting a personal Airtel SIM to a hosted voice agent is not automatically free. You need a supported call-forwarding destination or compatible telephony/SIP provider.
- ElevenLabs SIP trunking documentation currently describes the direct SIP trunk feature as Enterprise-only. Verify account eligibility before designing around it.
- Therefore, **first prove the experience in the ElevenLabs web/widget test environment**, then connect a real phone number only after the costs and routing are confirmed.

## Stage A: create the voice agent

1. Sign in at https://elevenlabs.io and open ElevenAgents.
2. Create a new agent named NESI.
3. Open agent-prompt.md in this repository and paste its content into the system prompt/instructions.
4. Select a multilingual voice/model supported by your account. Test English, conversational Tamil, and Tanglish; do not assume every voice speaks every language naturally.
5. In the agent's Advanced / Conversation Flow settings:
   - Enable interruptions / user barge-in.
   - Use eager or responsive turn-taking.
   - Start with a 5-8 second silence timeout for natural back-and-forth.
   - Optionally set a soft timeout around 3 seconds with a short filler such as "Hmm, let me think."
   - Set a sensible maximum call duration and usage limits.
6. Test using the built-in preview/widget before configuring phone numbers.

Official docs:
- Conversation flow and interruption settings: https://elevenlabs.io/docs/eleven-agents/customization/conversation-flow
- Webhook tools: https://elevenlabs.io/docs/eleven-agents/customization/tools/webhook-tools
- Post-call webhooks: https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks
- Phone-number/Twilio integration: https://elevenlabs.io/docs/eleven-agents/phone-numbers/twilio-integration/native-integration
- SIP trunking: https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking

## Stage B: n8n call summaries

1. Run n8n locally for testing: npx n8n.
2. Open http://localhost:5678.
3. Import n8n/elevenlabs-post-call-workflow.json.
4. The workflow receives an example post-call event and formats a summary. Test it with the webhook's test URL first.
5. For a live integration, expose a secure HTTPS endpoint and configure the ElevenLabs post-call transcription webhook to point to it. Do not point ElevenLabs at localhost: external services cannot reach your local machine.
6. Protect the webhook with a secret/authentication and verify ElevenLabs' webhook signature in production. The starter workflow is for local prototyping and is **not a signature-verifying production endpoint**.
7. Add a Telegram node after the summary node only after you create a Telegram bot and store its token as an n8n credential. Never put bot tokens in workflow code.
8. Keep audio recording disabled unless there is a clear need and appropriate consent/retention controls.

## Stage C: allow the agent to answer questions

General knowledge can be answered by the agent's selected LLM, but it must not invent personal facts about Yesu. Add an approved knowledge base for facts it may disclose, such as how to take a message, when to offer a callback, public project/portfolio facts Yesu has approved, and contact preferences.

For fresh or personal data, add specific authenticated webhook tools. Do not give the voice agent unrestricted access to arbitrary APIs or account actions. Ask for confirmation before sending messages, booking appointments, or taking irreversible actions.

## Stage D: connect actual phone calls

Do this only after the web voice prototype works:
1. Choose a supported telephony route and check costs for number rental, inbound minutes, and forwarding.
2. If using ElevenLabs native Twilio integration, purchase/configure a supported Twilio number and assign it to the agent.
3. To receive calls on the existing Airtel number, verify Airtel's available call-forwarding options and the destination number's compatibility and charges. Do not enable forwarding until a test number works end-to-end.
4. If a fully free route is mandatory, limit the first milestone to a browser-based voice agent or local SIP softphone test. PSTN access cannot be promised free.

## Acceptance tests

- Agent introduces itself as NESI, Yesu's AI assistant.
- Caller mode is respectful; owner notifications can be casual.
- English and Tamil/Tanglish are tested with real audio.
- Caller can interrupt NESI while she is speaking; NESI stops and listens.
- NESI resumes based on the new user turn without losing context.
- Unknown personal facts produce a clarifying question, not a fabricated answer.
- Post-call summary reaches the n8n test webhook.
- No API keys, caller secrets, or unneeded recordings are committed.
