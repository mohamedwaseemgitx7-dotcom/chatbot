/**
 * Messages in Supabase. Rows are immutable; RLS only allows writes into conversations the user owns.
 * Converts between UI messages (see hooks/useConversations.js) and `messages` rows.
 */
import { getSession, unwrap } from "./supabaseService";

const MESSAGE_COLUMNS = "id, conversation_id, sender, message, language, intent, confidence, message_type, metadata, created_at";
const LANGUAGES = new Set(["english", "tamil", "tanglish"]);
const clampUnit = (n) => (typeof n === "number" && Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : null);

/** UI message → row */
export function toMessageRow(conversationId, message) {
  const base = {
    id: message.id,
    conversation_id: conversationId,
    sender: message.role === "user" ? "user" : "assistant",
    language: LANGUAGES.has(message.language) ? message.language : null,
    // created_at comes from the database clock: device clocks can be wrong.
    // Writes are queued per conversation, so rows still land in the order they were sent.
  };

  if (message.kind === "image") {
    const image = message.image || {};
    return { ...base, message: "", message_type: "image", metadata: { image: { path: image.path ?? null, name: image.name ?? null, size: image.size ?? null } } };
  }
  if (message.kind === "image-result") {
    const r = message.result || {};
    const summary = ["Crop analysis", r.crop, r.condition].filter(Boolean).join(" · ");
    return { ...base, message: summary, message_type: "image", confidence: clampUnit(r.confidence), metadata: { result: r } };
  }
  return {
    ...base,
    message: message.text || "",
    message_type: "text",
    intent: message.intent || null,
    confidence: clampUnit(message.confidence),
    metadata: message.sources?.length ? { sources: message.sources } : {},
  };
}

/** Row → UI message. Unknown/partial rows degrade to a plain text message instead of failing. */
export function fromMessageRow(row) {
  const createdAt = Date.parse(row?.created_at) || Date.now();
  const role = row?.sender === "user" ? "user" : "assistant";
  const meta = row?.metadata && typeof row.metadata === "object" ? row.metadata : {};
  const common = { id: row?.id, role, language: row?.language || undefined, createdAt, ...(role === "user" ? { status: "sent" } : {}) };

  if (row?.message_type === "image" && role === "user") {
    const image = meta.image || {};
    return { ...common, kind: "image", image: { path: image.path || undefined, name: image.name || "Crop photo", size: image.size || 0 } };
  }
  if (row?.message_type === "image" && meta.result && typeof meta.result === "object") {
    return { ...common, kind: "image-result", result: meta.result };
  }
  const sources = Array.isArray(meta.sources) ? meta.sources.filter((s) => s?.title && /^https?:\/\//i.test(s?.url || "")) : [];
  return {
    ...common, kind: "text", text: typeof row?.message === "string" ? row.message : "",
    intent: row?.intent || undefined, confidence: row?.confidence ?? undefined, ...(sources.length ? { sources } : {}),
  };
}

/** Saves a message. Safe to call twice for the same message (retries): duplicates are ignored. */
export async function saveMessage(conversationId, message) {
  const { supabase } = await getSession();
  const result = await supabase.from("messages").insert(toMessageRow(conversationId, message));
  if (result.error?.code === "23505") return; // already saved
  unwrap(result, "save message");
}

/** All messages of one conversation, oldest first. */
export async function getMessages(conversationId) {
  const { supabase } = await getSession();
  const rows = unwrap(
    await supabase.from("messages").select(MESSAGE_COLUMNS).eq("conversation_id", conversationId).order("created_at", { ascending: true }).limit(500),
    "load messages",
  );
  return (rows || []).map(fromMessageRow);
}
