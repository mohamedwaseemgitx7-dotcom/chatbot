import { useCallback, useEffect, useRef, useState } from "react";
import { supabaseConfigured } from "../lib/supabase";
import { createConversation, deleteConversation, getConversations } from "../services/conversationService";
import { getMessages, saveMessage } from "../services/messageService";
import { deleteImage, saveImagePrediction, uploadImage } from "../services/storageService";
import { CloudError, getSession, toCloudError } from "../services/supabaseService";

const SAVE_FAILED = "Couldn't save this conversation to the server. It's kept on this device for now.";

/**
 * Keeps the conversation store in step with Supabase.
 * status: "local" (not configured) | "connecting" | "ready" | "error"
 * Everything is best-effort: if Supabase is unreachable the chat keeps working from the device cache.
 */
export function useCloudSync({ state, dispatch }) {
  const [status, setStatus] = useState(supabaseConfigured ? "connecting" : "local");
  const [notice, setNotice] = useState(null);
  const stateRef = useRef(state);
  stateRef.current = state;
  const statusRef = useRef(status);
  statusRef.current = status;
  const queues = useRef(new Map()); // conversationId → tail of its write queue
  const synced = useRef(new Set()); // ids known to exist on the server (updated before state re-renders)

  const find = (id) => stateRef.current.conversations.find((c) => c.id === id);

  /** Writes for one conversation run in order, so messages never arrive before their conversation. */
  const enqueue = useCallback((conversationId, task) => {
    const next = (queues.current.get(conversationId) || Promise.resolve()).catch(() => {}).then(task);
    queues.current.set(conversationId, next);
    return next;
  }, []);

  const ensureConversation = useCallback(async (conversationId, language) => {
    const conversation = find(conversationId);
    if (!conversation) throw new CloudError("not-found", "This conversation no longer exists.");
    if (conversation.synced || synced.current.has(conversationId)) return;
    await createConversation({ id: conversationId, title: conversation.title, language });
    synced.current.add(conversationId);
    dispatch({ type: "markSynced", conversationId });
  }, [dispatch]);

  /** Uploads conversations that were created while the server was unreachable. */
  const uploadLocalOnly = useCallback((conversations) => {
    for (const c of conversations) {
      const saved = c.messages.filter((m) => m.role === "assistant" || m.status === "sent");
      if (saved.length === 0) continue;
      enqueue(c.id, async () => {
        await ensureConversation(c.id, saved.find((m) => m.language)?.language);
        for (const m of saved) await saveMessage(c.id, m);
      }).catch((error) => setNotice(toCloudError(error, "upload local conversation").message));
    }
  }, [enqueue, ensureConversation]);

  // ---------- Connect, then load the conversation list ----------
  const connect = useCallback(async () => {
    if (!supabaseConfigured) return;
    setStatus("connecting");
    try {
      await getSession();
      const conversations = await getConversations();
      conversations.forEach((c) => synced.current.add(c.id));
      const localOnly = stateRef.current.conversations.filter((c) => !c.synced && !synced.current.has(c.id));
      dispatch({ type: "hydrate", conversations });
      setStatus("ready");
      setNotice(null);
      uploadLocalOnly(localOnly);
    } catch (error) {
      setStatus("error");
      setNotice(`${toCloudError(error, "connect").message} Your chats are saved on this device for now.`);
    }
  }, [dispatch, uploadLocalOnly]);

  useEffect(() => {
    connect();
    const onOnline = () => { if (statusRef.current === "error") connect(); };
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [connect]);

  // ---------- Load messages when a server conversation is opened ----------
  const active = state.conversations.find((c) => c.id === state.activeId);
  const needsMessages = status === "ready" && active?.synced && !active.loaded ? active.id : null;
  useEffect(() => {
    if (!needsMessages) return undefined;
    let cancelled = false;
    const since = Date.now();
    getMessages(needsMessages)
      .then((messages) => { if (!cancelled) dispatch({ type: "setMessages", conversationId: needsMessages, messages, since }); })
      .catch((error) => { if (!cancelled) setNotice(toCloudError(error, "load messages").message); });
    return () => { cancelled = true; };
  }, [needsMessages, dispatch]);

  // ---------- Save a finished question/answer pair ----------
  const saveExchange = useCallback((conversationId, { user, assistant, file }) => {
    if (statusRef.current !== "ready") return;
    enqueue(conversationId, async () => {
      await ensureConversation(conversationId, user.language || assistant.language);

      let userMessage = user;
      let path = null;
      if (user.kind === "image" && file) {
        path = await uploadImage(file, conversationId);
        userMessage = { ...user, image: { ...user.image, path } };
        dispatch({ type: "updateMessage", conversationId, messageId: user.id, patch: { image: userMessage.image } });
      }
      try {
        await saveMessage(conversationId, userMessage);
      } catch (error) {
        if (path) await deleteImage(path).catch(() => {}); // don't leave an orphaned photo behind
        throw error;
      }
      await saveMessage(conversationId, assistant);
      if (assistant.kind === "image-result" && path) {
        await saveImagePrediction({ messageId: user.id, path, result: assistant.result });
      }
    }).catch((error) => {
      toCloudError(error, "save exchange");
      setNotice(SAVE_FAILED);
    });
  }, [dispatch, enqueue, ensureConversation]);

  /** Deletes on the server first, so a chat never disappears locally only to come back on reload. */
  const deleteRemote = useCallback(async (conversation) => {
    const onServer = conversation.synced || synced.current.has(conversation.id);
    if (!onServer) return;
    if (statusRef.current !== "ready") {
      throw new CloudError("network", "Unable to connect to the server. Please check your internet connection and try again.");
    }
    try {
      await enqueue(conversation.id, () => deleteConversation(conversation.id));
      synced.current.delete(conversation.id);
    } catch (error) {
      throw toCloudError(error, "delete conversation");
    }
  }, [enqueue]);

  return { status, notice, dismissNotice: () => setNotice(null), saveExchange, deleteRemote, retryConnect: connect };
}
