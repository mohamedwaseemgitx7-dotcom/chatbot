import { useEffect, useMemo, useReducer } from "react";

/**
 * Conversation store. localStorage is the on-device cache; when Supabase is connected
 * (hooks/useCloudSync.js) the server copy is the source of truth and is merged in.
 *
 * Conversation: { id, title, createdAt, updatedAt, serverId, messages,
 *                 synced (saved in Supabase), loaded (messages fetched this session), lastMessage (list preview) }
 * Message:
 *   user:      { id, role: "user", kind: "text" | "image", text?, language?, image?: { url?, path?, name, size },
 *                status: "sending" | "sent" | "failed", error?: { message, retryable }, createdAt }
 *   assistant: { id, role: "assistant", kind: "text" | "image-result", text?, language?, result?, createdAt }
 * Timestamps are epoch milliseconds.
 */

const STORAGE_KEY = "farmerassist.conversations.v1";
const MAX_CONVERSATIONS = 50;
const MAX_MESSAGES = 200;

export const newId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

function titleFor(message) {
  if (message.kind === "image") return "Crop photo analysis";
  const oneLine = (message.text || "").replace(/\s+/g, " ").trim();
  return oneLine.length > 60 ? `${oneLine.slice(0, 57)}…` : oneLine || "New conversation";
}

// ---------- Persistence ----------
function loadState() {
  const empty = { conversations: [], activeId: null, pending: {} };
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!saved || !Array.isArray(saved.conversations)) return empty;
    const conversations = saved.conversations
      .filter((c) => c && typeof c.id === "string" && Array.isArray(c.messages))
      // Server-backed conversations are re-fetched each session; the cache shows until then.
      .map((c) => ({ ...c, synced: !!c.synced, loaded: !c.synced, messages: c.messages.map(reviveMessage) }));
    const activeId = conversations.some((c) => c.id === saved.activeId) ? saved.activeId : null;
    return { conversations, activeId, pending: {} };
  } catch {
    return empty;
  }
}

/** A message that was still sending when the page closed can't finish — mark it failed. */
function reviveMessage(m) {
  if (m.role !== "user" || m.status !== "sending") return m;
  return {
    ...m,
    status: "failed",
    error: m.kind === "image"
      ? { message: "This photo wasn't analysed. Please attach it again.", retryable: false }
      : { message: "This message wasn't sent. Please try again.", retryable: true },
  };
}

function toStorable(state) {
  return {
    activeId: state.activeId,
    conversations: state.conversations.slice(0, MAX_CONVERSATIONS).map((c) => ({
      ...c,
      // Photo previews are temporary blob: URLs — keep only the file details (and the Storage path).
      messages: c.messages.slice(-MAX_MESSAGES).map((m) => (m.image ? { ...m, image: { path: m.image.path, name: m.image.name, size: m.image.size } } : m)),
    })),
  };
}

// ---------- Reducer ----------
function updateConversation(state, id, fn) {
  return { ...state, conversations: state.conversations.map((c) => (c.id === id ? fn(c) : c)) };
}

function reducer(state, action) {
  switch (action.type) {
    case "create": {
      const now = Date.now();
      const conversation = {
        id: action.id, title: "New conversation", createdAt: now, updatedAt: now,
        serverId: null, messages: [], lastMessage: null, synced: false, loaded: true,
      };
      return { ...state, conversations: [conversation, ...state.conversations], activeId: action.id };
    }
    case "select":
      return { ...state, activeId: action.id };
    case "startNew":
      return { ...state, activeId: null };
    case "delete": {
      const { [action.id]: _removed, ...pending } = state.pending;
      return {
        conversations: state.conversations.filter((c) => c.id !== action.id),
        activeId: state.activeId === action.id ? null : state.activeId,
        pending,
      };
    }
    case "addMessage":
      return updateConversation(state, action.conversationId, (c) => ({
        ...c,
        title: c.messages.length === 0 && action.message.role === "user" ? titleFor(action.message) : c.title,
        updatedAt: action.message.createdAt,
        messages: [...c.messages, action.message],
      }));
    case "updateMessage":
      return updateConversation(state, action.conversationId, (c) => ({
        ...c,
        messages: c.messages.map((m) => (m.id === action.messageId ? { ...m, ...action.patch } : m)),
      }));
    case "hydrate": {
      // Server list wins; keep cached messages for display until fresh ones load, and keep
      // conversations that were never saved to the server (created while it was unreachable).
      const local = new Map(state.conversations.map((c) => [c.id, c]));
      const cloudIds = new Set(action.conversations.map((c) => c.id));
      const merged = action.conversations.map((c) => {
        const cached = local.get(c.id);
        return cached ? { ...c, messages: cached.messages, serverId: cached.serverId } : c;
      });
      const localOnly = state.conversations.filter((c) => !c.synced && !cloudIds.has(c.id));
      const conversations = [...merged, ...localOnly];
      const activeId = conversations.some((c) => c.id === state.activeId) ? state.activeId : null;
      return { ...state, conversations, activeId };
    }
    case "setMessages":
      return updateConversation(state, action.conversationId, (c) => {
        const fromServer = new Set(action.messages.map((m) => m.id));
        // Keep what the server doesn't have yet: unsent/failed messages, anything added while loading, and
        // messages whose upload never completed (not marked `cloud`) — those are re-sent by useCloudSync.
        const localExtra = c.messages.filter((m) => !fromServer.has(m.id) && (!m.cloud || m.status !== "sent" || m.createdAt >= action.since));
        const messages = [...action.messages, ...localExtra].sort((a, b) => a.createdAt - b.createdAt);
        return { ...c, messages, loaded: true };
      });
    case "markSynced":
      return updateConversation(state, action.conversationId, (c) => ({ ...c, synced: true }));
    case "setServerId":
      return updateConversation(state, action.conversationId, (c) => ({ ...c, serverId: action.serverId }));
    case "setPending": {
      const pending = { ...state.pending };
      if (action.pending) pending[action.conversationId] = action.pending;
      else delete pending[action.conversationId];
      return { ...state, pending };
    }
    default:
      return state;
  }
}

export function useConversations() {
  const [state, dispatch] = useReducer(reducer, undefined, loadState);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStorable(state)));
    } catch {
      // Storage full or blocked (private mode): the app keeps working in memory.
    }
  }, [state.conversations, state.activeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const sorted = useMemo(() => [...state.conversations].sort((a, b) => b.updatedAt - a.updatedAt), [state.conversations]);
  const active = state.conversations.find((c) => c.id === state.activeId) || null;

  return { state, dispatch, conversations: sorted, active, pending: active ? state.pending[active.id] || null : null };
}
