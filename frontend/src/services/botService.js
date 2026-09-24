/**
 * Assistant service — the only module that talks to the FastAPI backend.
 *
 * VITE_USE_BACKEND=true (default) calls /api/chat, /api/image/analyze and /api/voice/transcribe.
 * VITE_USE_BACKEND=false answers from the local rules below so the UI works on its own (demo mode).
 *
 * Every backend response is normalised here, so components never read raw response fields.
 */
import { ApiError, requestJson, uploadForm } from "./http";
import { detectLanguage } from "./languageDetector";

export const USE_BACKEND = import.meta.env.VITE_USE_BACKEND !== "false";

const LANGUAGES = new Set(["english", "tamil", "tanglish"]);

// ---------- Defensive readers ----------
const str = (v) => (typeof v === "string" && v.trim() ? v.trim() : "");
const firstStr = (...values) => values.map(str).find(Boolean) || "";
const strList = (v) => (Array.isArray(v) ? v.map(str).filter(Boolean) : []);
const lang = (v, fallback) => (LANGUAGES.has(v) ? v : fallback);

/** Accepts 0–1 or 0–100, returns 0–1 or null when missing/invalid. */
function unitConfidence(v) {
  const n = typeof v === "string" ? Number.parseFloat(v) : v;
  if (typeof n !== "number" || !Number.isFinite(n)) return null;
  const unit = n > 1 ? n / 100 : n;
  return Math.min(1, Math.max(0, unit));
}

/** Only http(s) links with a title are kept; everything else is dropped. */
function normalizeSources(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((s) => ({ title: str(s?.title), url: str(s?.url), publisher: str(s?.publisher) }))
    .filter((s) => s.title && /^https?:\/\//i.test(s.url))
    .slice(0, 3);
}

function normalizeChat(data, fallbackLanguage) {
  const body = data?.data && typeof data.data === "object" ? data.data : data;
  const text = firstStr(body?.response, body?.message, body?.answer, body?.result);
  if (!text) throw new ApiError("bad-response");
  return {
    text,
    language: lang(body?.language, fallbackLanguage),
    conversationId: str(body?.conversation_id) || null,
    intent: str(body?.intent) || null,
    confidence: unitConfidence(body?.confidence),
    sources: normalizeSources(body?.sources),
  };
}

/**
 * @returns {{ kind: "result", result: object } | { kind: "text", text: string }}
 * "uncertain" / "model_unavailable" come back as plain assistant text — never as a fake prediction.
 */
function normalizeImage(data) {
  const body = data?.data ?? data?.result ?? data;
  const status = str(body?.status) || "ok";
  if (status === "model_unavailable") {
    return { kind: "text", text: "Photo analysis isn't available right now — the crop disease model is not ready yet. You can still describe the problem in words." };
  }
  if (status !== "ok") {
    const message = str(body?.message) || "I could not confidently identify a supported crop or condition from this image.";
    const hint = "Supported crops: paddy, tomato, chilli and banana. Try a clear, close photo of one affected leaf in daylight.";
    return { kind: "text", text: `${message}\n\n${hint}` };
  }
  const crop = firstStr(body?.crop, body?.crop_name);
  const condition = firstStr(body?.prediction, body?.disease, body?.label);
  if (!crop && !condition) throw new ApiError("bad-response");
  return {
    kind: "result",
    result: {
      crop,
      condition,
      confidence: unitConfidence(body?.confidence),
      causes: strList(body?.possible_causes),
      nextSteps: strList(body?.recommended_next_steps),
      disclaimer: str(body?.disclaimer),
      sources: normalizeSources(body?.sources),
      model: { name: str(body?.model_name), version: str(body?.model_version), datasetVersion: str(body?.dataset_version) },
    },
  };
}

function normalizeTranscript(data) {
  const body = data?.data ?? data;
  return {
    text: firstStr(body?.text, body?.transcript, body?.transcription),
    language: lang(body?.detected_language ?? body?.language, "english"),
  };
}

// ---------- Demo mode (no backend) ----------
const GREETING_WORDS = /^(hi+|hii+|hai|hello|helo|hey|vanakk?am|வணக்கம்|good (morning|evening|afternoon))(?=[\s!.,?]|$)/i;
const THANKS_WORDS = /(thanks|thank you|nandri|நன்றி)/i;
const IDENTITY_WORDS = /(who are you|yaaru nee|nee yaaru|neenga yaaru|நீங்கள் யார்|நீ யார்)/i;

const REPLIES = {
  greeting: {
    english: "Hello! 👋 I'm FarmerAssist 🌾\nAsk me about crops, pests, fertilizer or government schemes.",
    tamil: "வணக்கம்! 👋 நான் FarmerAssist 🌾\nபயிர், பூச்சி, உரம், அரசுத் திட்டங்கள் பற்றி கேளுங்கள்.",
    tanglish: "Vanakkam! 👋 Naan FarmerAssist 🌾\nPayir, poochi, uram, govt scheme pathi enna venumnaalum kelunga.",
  },
  thanks: {
    english: "You're welcome! Wishing you a good harvest 🌱",
    tamil: "மகிழ்ச்சி! நல்ல விளைச்சல் கிடைக்க வாழ்த்துகள் 🌱",
    tanglish: "Santhosham! Nalla vilaichal kidaikka vaazhthukkal 🌱",
  },
  identity: {
    english: "I'm FarmerAssist, an assistant for Tamil Nadu farmers. I reply in Tamil, English or Tanglish — the same way you write to me.",
    tamil: "நான் FarmerAssist, தமிழ்நாடு விவசாயிகளுக்கான உதவியாளர். நீங்கள் எழுதும் மொழியிலேயே பதில் சொல்வேன்.",
    tanglish: "Naan FarmerAssist, Tamil Nadu vivasayigalukkana assistant. Neenga endha language la kekkureengalo adhe language la reply panren.",
  },
  notConnected: {
    english: "Demo mode: the farming knowledge base isn't connected, so I can only greet you for now.",
    tamil: "டெமோ முறை: விவசாய அறிவுத் தளம் இன்னும் இணைக்கப்படவில்லை.",
    tanglish: "Demo mode: vivasaya knowledge base innum connect aagala.",
  },
};

function demoIntent(text) {
  if (GREETING_WORDS.test(text)) return "greeting";
  if (THANKS_WORDS.test(text)) return "thanks";
  if (IDENTITY_WORDS.test(text)) return "identity";
  return "notConnected";
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------- Public API ----------

/** @returns {Promise<{ text: string, language: string, conversationId: string | null }>} */
export async function sendChatMessage(message, { conversationId = null, signal } = {}) {
  const language = detectLanguage(message);

  if (!USE_BACKEND) {
    await wait(700);
    return { text: REPLIES[demoIntent(message.trim())][language], language, conversationId };
  }

  const data = await requestJson("/chat", {
    json: { message, language, conversation_id: conversationId },
    timeoutMs: 45000,
    signal,
  });
  return normalizeChat(data, language);
}

/**
 * @returns {Promise<{ kind: "result", result: object } | { kind: "text", text: string }>}
 */
export async function analyzeCropImage(file, { conversationId = null, onUploaded, signal } = {}) {
  if (!USE_BACKEND) {
    await wait(600);
    onUploaded?.();
    await wait(1200);
    return { kind: "text", text: "Demo mode: crop photo analysis works once the backend is connected." };
  }

  const form = new FormData();
  form.append("file", file);
  if (conversationId) form.append("conversation_id", conversationId);
  const data = await uploadForm("/image/analyze", form, { timeoutMs: 90000, onUploaded, signal });
  return normalizeImage(data);
}

/** @returns {Promise<{ text: string, language: string }>} text is "" when nothing was recognised */
export async function transcribeVoice(blob, { signal } = {}) {
  if (!USE_BACKEND) throw new ApiError("unavailable");

  const ext = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm";
  const form = new FormData();
  form.append("audio", blob, `voice.${ext}`);
  const data = await requestJson("/voice/transcribe", { form, timeoutMs: 60000, signal });
  return normalizeTranscript(data);
}

/** Lightweight reachability check for the header status. */
export async function checkHealth() {
  if (!USE_BACKEND) return "demo";
  try {
    const data = await requestJson("/health", { method: "GET", timeoutMs: 6000 });
    return data?.status ? "online" : "unreachable";
  } catch (error) {
    return error?.kind === "offline" ? "offline" : "unreachable";
  }
}
