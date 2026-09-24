import { useCallback, useRef } from "react";
import { analyzeCropImage, sendChatMessage } from "../services/botService";
import { toFriendlyError } from "../services/errors";
import { detectLanguage } from "../services/languageDetector";
import { TokenBucket } from "../services/rateLimiter";
import { useCooldown } from "./useCooldown";
import { newId } from "./useConversations";

/** Sending, image analysis and retry, on top of the conversation store. `sync` saves results to Supabase. */
export function useAssistant({ state, dispatch }, sync) {
  const stateRef = useRef(state);
  stateRef.current = state;
  const limiter = useRef(new TokenBucket({ capacity: 5, refillPerSecond: 0.5 }));
  // Selected photos, kept in memory so a failed analysis can be retried without re-picking the file.
  const files = useRef(new Map());
  // Messages just added (the store may not have re-rendered yet when a fast reply arrives).
  const userSnapshot = useRef(new Map());
  // Server rate limits (HTTP 429): per-feature countdowns shown in the composer.
  const cooldown = useCooldown();

  const findConversation = (id) => stateRef.current.conversations.find((c) => c.id === id);

  /** Uses the open conversation, or creates one on the first message. */
  const ensureConversation = useCallback(() => {
    const { activeId } = stateRef.current;
    if (activeId && findConversation(activeId)) return activeId;
    const id = newId();
    dispatch({ type: "create", id });
    return id;
  }, [dispatch]);

  const gate = useCallback((conversationId, kind = "chat") => {
    const wait = cooldown.remaining(kind);
    if (wait > 0) {
      return { ok: false, error: `Rate limit reached. Try again in ${wait} seconds.` };
    }
    if (conversationId && stateRef.current.pending[conversationId]) {
      return { ok: false, error: "Please wait for the current reply to finish." };
    }
    const { allowed, retryInSeconds } = limiter.current.tryConsume();
    if (!allowed) {
      return { ok: false, error: `You're sending messages too quickly. Please wait ${retryInSeconds} s and try again.` };
    }
    return { ok: true };
  }, [cooldown]);

  /** Runs one request for a user message and records the outcome. */
  const run = useCallback(
    async (conversationId, messageId, context, request) => {
      const setPending = (pending) => dispatch({ type: "setPending", conversationId, pending });
      setPending(context === "image" ? { kind: "image", stage: "uploading" } : { kind: "text" });
      dispatch({ type: "updateMessage", conversationId, messageId, patch: { status: "sending", error: undefined } });

      try {
        // The conversation id doubles as the backend's conversation id, so both sides refer to the same chat.
        const serverId = findConversation(conversationId)?.serverId ?? conversationId;
        const reply = await request(serverId, (stage) => setPending({ kind: "image", stage }));
        dispatch({ type: "updateMessage", conversationId, messageId, patch: { status: "sent" } });
        if (reply.serverId && reply.serverId !== serverId) {
          dispatch({ type: "setServerId", conversationId, serverId: reply.serverId });
        }
        const assistant = { id: newId(), role: "assistant", createdAt: Date.now(), ...reply.message };
        dispatch({ type: "addMessage", conversationId, message: assistant });

        const user = findConversation(conversationId)?.messages.find((m) => m.id === messageId) || userSnapshot.current.get(messageId);
        sync?.saveExchange(conversationId, { user: { ...user, status: "sent" }, assistant, file: files.current.get(messageId) });
        userSnapshot.current.delete(messageId);
        if (context === "image") files.current.delete(messageId);
      } catch (error) {
        if (error?.status === 429) cooldown.start(context === "image" ? "image" : "chat", error.retryAfter);
        dispatch({ type: "updateMessage", conversationId, messageId, patch: { status: "failed", error: toFriendlyError(error, context) } });
      } finally {
        setPending(null);
      }
    },
    [dispatch, sync, cooldown],
  );

  const requestChat = (text) => async (serverId) => {
    const reply = await sendChatMessage(text, { conversationId: serverId });
    return {
      serverId: reply.conversationId,
      message: {
        kind: "text", text: reply.text, language: reply.language, intent: reply.intent, confidence: reply.confidence,
        sources: reply.sources,
      },
    };
  };

  const requestImage = (file) => async (serverId, setStage) => {
    let timer;
    try {
      const reply = await analyzeCropImage(file, {
        conversationId: serverId,
        onUploaded: () => {
          setStage("analyzing");
          timer = setTimeout(() => setStage("checking"), 1500);
        },
      });
      return {
        serverId: null,
        message: reply.kind === "result" ? { kind: "image-result", result: reply.result } : { kind: "text", text: reply.text },
      };
    } finally {
      clearTimeout(timer);
    }
  };

  /** @returns {{ ok: boolean, error?: string }} */
  const sendText = useCallback(
    (raw) => {
      const text = raw.trim();
      if (!text) return { ok: false };
      const check = gate(stateRef.current.activeId);
      if (!check.ok) return check;

      const conversationId = ensureConversation();
      const message = { id: newId(), role: "user", kind: "text", text, language: detectLanguage(text), status: "sending", createdAt: Date.now() };
      userSnapshot.current.set(message.id, message);
      dispatch({ type: "addMessage", conversationId, message });
      run(conversationId, message.id, "chat", requestChat(text));
      return { ok: true };
    },
    [dispatch, ensureConversation, gate, run],
  );

  /** @returns {{ ok: boolean, error?: string }} */
  const sendImage = useCallback(
    (file) => {
      const check = gate(stateRef.current.activeId, "image");
      if (!check.ok) return check;

      const conversationId = ensureConversation();
      const message = {
        id: newId(),
        role: "user",
        kind: "image",
        image: { url: URL.createObjectURL(file), name: file.name, size: file.size },
        status: "sending",
        createdAt: Date.now(),
      };
      files.current.set(message.id, file);
      userSnapshot.current.set(message.id, message);
      dispatch({ type: "addMessage", conversationId, message });
      run(conversationId, message.id, "image", requestImage(file));
      return { ok: true };
    },
    [dispatch, ensureConversation, gate, run],
  );

  const retry = useCallback(
    (conversationId, messageId) => {
      if (stateRef.current.pending[conversationId]) return;
      const message = findConversation(conversationId)?.messages.find((m) => m.id === messageId);
      if (!message || message.status !== "failed") return;
      if (cooldown.remaining(message.kind === "image" ? "image" : "chat") > 0) return;

      if (message.kind === "text") {
        run(conversationId, messageId, "chat", requestChat(message.text));
      } else {
        const file = files.current.get(messageId);
        if (file) run(conversationId, messageId, "image", requestImage(file));
      }
    },
    [run, cooldown],
  );

  const canRetry = useCallback((message) => message.kind === "text" || files.current.has(message.id), []);

  return { sendText, sendImage, retry, canRetry, cooldown };
}
