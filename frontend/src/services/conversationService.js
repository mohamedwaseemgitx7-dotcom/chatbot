/**
 * Conversations in Supabase. RLS scopes every query to the signed-in user, so ownership can't be
 * bypassed by passing someone else's conversation id — those rows are simply invisible.
 */
import { fromMessageRow } from "./messageService";
import { removeConversationFiles } from "./storageService";
import { CloudError, getSession, unwrap } from "./supabaseService";

const LIST_LIMIT = 50;

/** Row → UI conversation (messages are loaded separately when it's opened). */
function fromConversationRow(row) {
  const last = Array.isArray(row?.messages) && row.messages[0] ? fromMessageRow(row.messages[0]) : null;
  return {
    id: row.id,
    title: row.title || "New conversation",
    createdAt: Date.parse(row.created_at) || Date.now(),
    updatedAt: Date.parse(row.updated_at) || Date.now(),
    serverId: null,
    messages: [],
    lastMessage: last,
    loaded: false,
    synced: true,
  };
}

export async function createConversation({ id, title, language }) {
  const { supabase, userId } = await getSession();
  const row = unwrap(
    await supabase.from("conversations")
      .insert({ id, user_id: userId, title: (title || "New conversation").slice(0, 200), language: language || null })
      .select("id, title, created_at, updated_at")
      .single(),
    "create conversation",
  );
  return fromConversationRow(row);
}

/** The user's most recent conversations, each with its latest message for the sidebar preview. */
export async function getConversations() {
  const { supabase } = await getSession();
  const rows = unwrap(
    await supabase.from("conversations")
      .select("id, title, created_at, updated_at, messages(id, sender, message, message_type, metadata, language, created_at)")
      .order("updated_at", { ascending: false })
      .order("created_at", { referencedTable: "messages", ascending: false })
      .limit(1, { referencedTable: "messages" })
      .limit(LIST_LIMIT),
    "load conversations",
  );
  return (rows || []).map(fromConversationRow);
}

export async function getConversation(id) {
  const { supabase } = await getSession();
  const row = unwrap(
    await supabase.from("conversations").select("id, title, created_at, updated_at").eq("id", id).maybeSingle(),
    "load conversation",
  );
  if (!row) throw new CloudError("not-found", "This conversation couldn't be found. It may have been deleted.");
  return fromConversationRow(row);
}

export async function updateConversationTitle(id, title) {
  const { supabase } = await getSession();
  const rows = unwrap(
    await supabase.from("conversations").update({ title: title.trim().slice(0, 200) || "New conversation" }).eq("id", id).select("id"),
    "rename conversation",
  );
  if (!rows?.length) throw new CloudError("not-found", "This conversation couldn't be found. It may have been deleted.");
}

/** Deletes the conversation, its messages (cascade) and its uploaded files. */
export async function deleteConversation(id) {
  const { supabase } = await getSession();
  await removeConversationFiles(id);
  unwrap(await supabase.from("conversations").delete().eq("id", id).select("id"), "delete conversation");
}
