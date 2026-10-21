const $ = (id) => document.getElementById(id);

const statusPill = document.querySelector(".pill");
const statusText = $("statusText");
const startBtn = $("startBtn");
const stopBtn = $("stopBtn");
const modeSelect = $("mode");
const languageSelect = $("language");
const callerNameWrap = $("callerNameWrap");
const callerNameInput = $("callerName");
const transcript = $("transcript");
const textForm = $("textForm");
const textInput = $("textInput");
const sendTextBtn = $("sendTextBtn");

let socket = null;
let audioContext = null;
let micStream = null;
let micSource = null;
let processor = null;
let muteGain = null;
let nextPlaybackTime = 0;
let activeSources = new Set();
let connected = false;
let sessionStarting = false;
let mergeSpeaker = null;

function setStatus(text, state = "ready") {
  statusText.textContent = text;
  statusPill.classList.toggle("connected", state === "connected");
  statusPill.classList.toggle("error", state === "error");
}

function addMessage(speaker, text) {
  if (!text || !text.trim()) return;
  const existingEmpty = $("emptyState");
  if (existingEmpty) existingEmpty.remove();

  const key = speaker === "nesi" ? "nesi" : "you";
  const last = transcript.lastElementChild;
  // Gemini may emit cumulative or incremental transcription fragments within one turn.
  if (mergeSpeaker === key && last && last.classList.contains("message") && last.dataset.speaker === key) {
    const body = last.querySelector(".message-body");
    const old = body.textContent;
    if (text.startsWith(old)) body.textContent = text;
    else if (!old.startsWith(text)) body.textContent = old + text;
    transcript.scrollTop = transcript.scrollHeight;
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "message" + (key === "nesi" ? " nesi" : "");
  wrapper.dataset.speaker = key;
  const meta = document.createElement("span");
  meta.className = "message-meta";
  meta.textContent = key === "nesi" ? "NESI" : "You";
  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;
  wrapper.append(meta, body);
  transcript.appendChild(wrapper);
  mergeSpeaker = key;
  transcript.scrollTop = transcript.scrollHeight;
}

function bytesToBase64(bytes) {
  let binary = "";
  const step = 0x8000;
  for (let i = 0; i < bytes.length; i += step) {
    binary += String.fromCharCode(...bytes.subarray(i, i + step));
  }
  return btoa(binary);
}

function downsampleTo16k(floatBuffer, inputRate) {
  const targetRate = 16000;
  if (inputRate === targetRate) {
    const pcm = new Int16Array(floatBuffer.length);
    for (let i = 0; i < floatBuffer.length; i++) {
      const s = Math.max(-1, Math.min(1, floatBuffer[i]));
      pcm[i] = s < 0 ? s * 32768 : s * 32767;
    }
    return new Uint8Array(pcm.buffer);
  }
  const ratio = inputRate / targetRate;
  const outputLength = Math.floor(floatBuffer.length / ratio);
  const output = new Int16Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), floatBuffer.length);
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += floatBuffer[j];
      count++;
    }
    const sample = Math.max(-1, Math.min(1, count ? sum / count : 0));
    output[i] = sample < 0 ? sample * 32768 : sample * 32767;
  }
  return new Uint8Array(output.buffer);
}

function stopPlayback() {
  for (const source of activeSources) {
    try { source.stop(); } catch (_) {}
    try { source.disconnect(); } catch (_) {}
  }
  activeSources.clear();
  nextPlaybackTime = audioContext ? audioContext.currentTime : 0;
}

function playPcm24k(base64) {
  if (!audioContext || !connected) return;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const samples = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
  const floats = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) floats[i] = samples[i] / 32768;
  const buffer = audioContext.createBuffer(1, floats.length, 24000);
  buffer.copyToChannel(floats, 0);
  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioContext.destination);
  const startAt = Math.max(audioContext.currentTime + 0.025, nextPlaybackTime);
  source.start(startAt);
  nextPlaybackTime = startAt + buffer.duration;
  activeSources.add(source);
  source.onended = () => {
    activeSources.delete(source);
    source.disconnect();
  };
}

async function startMicrophone() {
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  await audioContext.resume();
  micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: false
  });
  micSource = audioContext.createMediaStreamSource(micStream);
  processor = audioContext.createScriptProcessor(4096, 1, 1);
  muteGain = audioContext.createGain();
  muteGain.gain.value = 0;
  processor.onaudioprocess = (event) => {
    if (!socket || socket.readyState !== WebSocket.OPEN || !connected) return;
    const input = event.inputBuffer.getChannelData(0);
    const pcmBytes = downsampleTo16k(input, audioContext.sampleRate);
    socket.send(JSON.stringify({ type: "audio", data: bytesToBase64(pcmBytes) }));
  };
  micSource.connect(processor);
  processor.connect(muteGain);
  muteGain.connect(audioContext.destination);
}

function cleanUp() {
  connected = false;
  sessionStarting = false;
  if (processor) {
    processor.disconnect();
    processor.onaudioprocess = null;
    processor = null;
  }
  if (micSource) { try { micSource.disconnect(); } catch (_) {} micSource = null; }
  if (muteGain) { try { muteGain.disconnect(); } catch (_) {} muteGain = null; }
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
    micStream = null;
  }
  if (socket) {
    const old = socket;
    socket = null;
    if (old.readyState === WebSocket.OPEN) {
      try { old.send(JSON.stringify({ type: "end" })); } catch (_) {}
      old.close();
    }
  }
  if (audioContext) {
    stopPlayback();
    audioContext.close().catch(() => {});
    audioContext = null;
  }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  modeSelect.disabled = false;
  languageSelect.disabled = false;
  callerNameInput.disabled = false;
  textInput.disabled = true;
  sendTextBtn.disabled = true;
}

async function startSession() {
  if (sessionStarting || connected) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("Microphone requires localhost or HTTPS", "error");
    return;
  }
  sessionStarting = true;
  startBtn.disabled = true;
  modeSelect.disabled = true;
  languageSelect.disabled = true;
  callerNameInput.disabled = true;
  setStatus("Connecting…");
  const params = new URLSearchParams({
    mode: modeSelect.value,
    language: languageSelect.value,
    caller_name: callerNameInput.value.trim()
  });
  const scheme = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${scheme}//${location.host}/ws/live?${params.toString()}`);

  socket.onmessage = async (event) => {
    let message;
    try { message = JSON.parse(event.data); } catch (_) { return; }
    if (message.type === "status" && message.state === "connected") {
      connected = true;
      sessionStarting = false;
      setStatus("Connected · listening", "connected");
      startBtn.disabled = true;
      stopBtn.disabled = false;
      textInput.disabled = false;
      sendTextBtn.disabled = false;
      try {
        await startMicrophone();
      } catch (error) {
        setStatus("Microphone permission denied", "error");
        addMessage("nesi", "I couldn't access the microphone. Please allow microphone access and start again.");
        cleanUp();
      }
    } else if (message.type === "audio") {
      playPcm24k(message.data);
    } else if (message.type === "transcript") {
      addMessage(message.speaker, message.text);
    } else if (message.type === "interrupted") {
      mergeSpeaker = null;
      stopPlayback();
      setStatus("You interrupted NESI", "connected");
    } else if (message.type === "turn_complete") {
      mergeSpeaker = null;
      setStatus("Connected · listening", "connected");
    } else if (message.type === "error") {
      setStatus("Connection error", "error");
      addMessage("nesi", message.message || "The voice session failed.");
      cleanUp();
    }
  };

  socket.onerror = () => {
    setStatus("Connection failed", "error");
    addMessage("nesi", "Couldn't connect to the local NESI server. Check that FastAPI is running and your Gemini API key is configured.");
  };
  socket.onclose = () => {
    if (connected || sessionStarting) {
      cleanUp();
      setStatus("Session ended");
    }
  };
}

function endSession() {
  if (socket?.readyState === WebSocket.OPEN) {
    try { socket.send(JSON.stringify({ type: "end" })); } catch (_) {}
  }
  cleanUp();
  setStatus("Session ended");
}

modeSelect.addEventListener("change", () => {
  callerNameWrap.classList.toggle("hidden", modeSelect.value !== "caller");
});
$("startBtn").addEventListener("click", startSession);
$("stopBtn").addEventListener("click", endSession);
$("clearBtn").addEventListener("click", () => {
  transcript.innerHTML = '<div id="emptyState" class="empty-state"><span class="sound-mark">〰</span><strong>Your conversation appears here</strong><span>Start a session and say hello.</span></div>';
  mergeSpeaker = null;
});
textForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = textInput.value.trim();
  if (!text || !socket || socket.readyState !== WebSocket.OPEN || !connected) return;
  socket.send(JSON.stringify({ type: "text", text }));
  addMessage("you", text);
  textInput.value = "";
});
window.addEventListener("beforeunload", cleanUp);
modeSelect.dispatchEvent(new Event("change"));