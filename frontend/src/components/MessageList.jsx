import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowDownIcon } from "./Icons";
import MessageBubble from "./MessageBubble";
import PendingReply from "./PendingReply";
import WelcomeScreen from "./WelcomeScreen";
import { formatDayLabel, sameDay } from "../utils/format";

const NEAR_BOTTOM_PX = 96;
const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function MessageList({ conversation, pending, onRetry, canRetry, onExample, retryBlocked = false }) {
  const scrollRef = useRef(null);
  const innerRef = useRef(null);
  const atBottomRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const messages = conversation?.messages ?? [];
  const conversationId = conversation?.id ?? null;
  const lastMessage = messages[messages.length - 1];

  // Only messages that arrive while you watch get the entrance animation — not restored history.
  const baseline = useRef({ id: undefined, ids: new Set() });
  if (baseline.current.id !== conversationId) {
    const fromDraft = baseline.current.id === null; // first message of a brand-new chat should animate
    baseline.current = { id: conversationId, ids: fromDraft ? new Set() : new Set(messages.map((m) => m.id)) };
  }

  const scrollToBottom = useCallback((smooth) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth && !prefersReducedMotion() ? "smooth" : "auto" });
  }, []);

  const onScroll = () => {
    const el = scrollRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
    atBottomRef.current = atBottom;
    setShowJump((prev) => (prev === !atBottom ? prev : !atBottom));
  };

  // Opening a conversation starts at its latest message.
  useLayoutEffect(() => {
    atBottomRef.current = true;
    setShowJump(false);
    scrollToBottom(false);
  }, [conversationId, scrollToBottom]);

  // New content: follow it if you were at the bottom, or if you just sent something.
  useEffect(() => {
    if (atBottomRef.current || lastMessage?.role === "user") scrollToBottom(true);
  }, [lastMessage?.id, lastMessage?.role, pending?.kind, pending?.stage, scrollToBottom]);

  // Photos and cards change height after they render; stay pinned to the bottom while that happens.
  useEffect(() => {
    const inner = innerRef.current;
    if (!inner || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(() => { if (atBottomRef.current) scrollToBottom(false); });
    observer.observe(inner);
    return () => observer.disconnect();
  }, [scrollToBottom]);

  const retryOne = useCallback((messageId) => onRetry(conversationId, messageId), [onRetry, conversationId]);
  const loading = conversation?.synced && !conversation.loaded && messages.length === 0;
  const empty = messages.length === 0 && !pending && !loading;

  return (
    <div className="messages-wrap">
      <div className="messages" ref={scrollRef} onScroll={onScroll}>
        <div className="messages__inner" ref={innerRef}>
          {loading ? (
            <p className="messages__loading" role="status"><span className="spinner" aria-hidden="true" /> Loading conversation…</p>
          ) : empty ? (
            <WelcomeScreen onExample={onExample} />
          ) : (
            <div className="messages__log" role="log" aria-label="Conversation">
              {messages.map((m, i) => {
                const prev = messages[i - 1];
                const date = new Date(m.createdAt);
                const newDay = !prev || !sameDay(new Date(prev.createdAt), date);
                return (
                  <Fragment key={m.id}>
                    {newDay && <div className="day-divider"><span>{formatDayLabel(date)}</span></div>}
                    <MessageBubble
                      message={m}
                      animate={!baseline.current.ids.has(m.id)}
                      canRetry={m.status === "failed" && canRetry(m)}
                      retryDisabled={!!pending || retryBlocked}
                      onRetry={retryOne}
                    />
                  </Fragment>
                );
              })}
              {pending && <PendingReply pending={pending} />}
            </div>
          )}
        </div>
      </div>

      {showJump && !empty && (
        <button type="button" className="jump-to-latest" onClick={() => scrollToBottom(true)} aria-label="Scroll to latest message">
          <ArrowDownIcon />
        </button>
      )}
    </div>
  );
}
