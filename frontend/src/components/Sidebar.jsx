import { useEffect, useMemo, useRef, useState } from "react";
import ConversationItem from "./ConversationItem";
import { CloseIcon, NewChatIcon, SearchIcon } from "./Icons";
import "./Sidebar.css";

function matches(conversation, query) {
  if (conversation.title.toLowerCase().includes(query)) return true;
  return conversation.messages.some((m) => typeof m.text === "string" && m.text.toLowerCase().includes(query));
}

/**
 * Conversation history. A fixed column on wide screens; a modal drawer on small ones (`drawer`).
 */
export default function Sidebar({ id, conversations, activeId, onSelect, onNewChat, onDelete, drawer, open, onClose }) {
  const [query, setQuery] = useState("");
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const modal = drawer && open;

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? conversations.filter((c) => matches(c, q)) : conversations;
  }, [conversations, query]);

  // Drawer: focus moves inside, Escape closes, Tab stays inside.
  useEffect(() => {
    if (!modal) return undefined;
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); return; }
      if (e.key !== "Tab") return;
      const focusable = panelRef.current?.querySelectorAll("button:not(:disabled), input, [href]");
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [modal, onClose]);

  return (
    <aside
      id={id}
      ref={panelRef}
      className={`sidebar${drawer ? " sidebar--drawer" : ""}${modal ? " sidebar--open" : ""}`}
      aria-label="Conversations"
      role={modal ? "dialog" : undefined}
      aria-modal={modal ? "true" : undefined}
      inert={drawer && !open ? "" : undefined}
    >
      {drawer && (
        <div className="sidebar__top">
          <h2 className="sidebar__heading">Conversations</h2>
          <button ref={closeRef} type="button" className="icon-btn" onClick={onClose} aria-label="Close conversations">
            <CloseIcon />
          </button>
        </div>
      )}

      <div className="sidebar__controls">
        <button type="button" className="btn btn--primary sidebar__new" onClick={onNewChat}>
          <NewChatIcon /> New chat
        </button>
        <label className="search">
          <SearchIcon />
          <span className="visually-hidden">Search conversations</span>
          <input type="search" placeholder="Search conversations" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>

      <nav className="sidebar__list" aria-label="Conversation history">
        {conversations.length === 0 ? (
          <p className="sidebar__empty">No conversations yet. Your questions will be saved here.</p>
        ) : visible.length === 0 ? (
          <p className="sidebar__empty">No conversations match “{query.trim()}”.</p>
        ) : (
          <ul>
            {visible.map((c) => (
              <ConversationItem key={c.id} conversation={c} active={c.id === activeId} onSelect={onSelect} onDelete={onDelete} />
            ))}
          </ul>
        )}
      </nav>

      <p className="sidebar__footer">AI answers can be wrong. Check important decisions with your local agriculture officer.</p>
    </aside>
  );
}
