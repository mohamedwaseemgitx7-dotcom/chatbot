import { useCallback, useEffect, useRef, useState } from "react";
import Composer from "./Composer";
import { CloseIcon, UploadIcon, WifiOffIcon } from "./Icons";
import MessageList from "./MessageList";
import { validateImage, validateImageContent } from "../utils/validateImage";
import "./Chat.css";

const hasFiles = (event) => [...(event.dataTransfer?.types || [])].includes("Files");

export default function ChatWindow({ conversation, pending, assistant, connection, syncNotice, onDismissSyncNotice, onRetrySync }) {
  const [attachment, setAttachment] = useState(null); // { file, url }
  const [feedback, setFeedback] = useState(null); // { type: "error" | "info", text }
  const [dragging, setDragging] = useState(false);
  const attachmentRef = useRef(null);
  attachmentRef.current = attachment;

  const clearAttachment = useCallback(() => {
    setAttachment((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return null;
    });
  }, []);

  // Free the preview when leaving the page.
  useEffect(() => () => { if (attachmentRef.current) URL.revokeObjectURL(attachmentRef.current.url); }, []);

  // Messages about the previous conversation don't belong in the next one.
  useEffect(() => { setFeedback(null); }, [conversation?.id]);

  const attach = useCallback(async (file) => {
    const error = validateImage(file) || (await validateImageContent(file));
    if (error) {
      setFeedback({ type: "error", text: error });
      return;
    }
    setFeedback(null);
    setAttachment((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return { file, url: URL.createObjectURL(file) };
    });
  }, []);

  function analyze() {
    if (!attachment) return;
    const result = assistant.sendImage(attachment.file);
    if (result.ok) clearAttachment();
    else if (result.error) setFeedback({ type: "error", text: result.error });
  }

  function sendExample(text) {
    const result = assistant.sendText(text);
    if (!result.ok && result.error) setFeedback({ type: "error", text: result.error });
  }

  // ---------- Drag & drop a photo anywhere on the chat ----------
  const onDragOver = (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    if (!dragging) setDragging(true);
  };
  const onDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
  };
  const onDrop = (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) attach(file);
  };

  return (
    <section className="chat" aria-label="Chat" onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      {connection === "offline" && (
        <div className="chat__banner" role="status">
          <WifiOffIcon />
          <span>You're offline. You can read your chats, but new questions won't send until you reconnect.</span>
        </div>
      )}

      {syncNotice && connection !== "offline" && (
        <div className="chat__banner chat__banner--sync" role="status">
          <span>{syncNotice}</span>
          {onRetrySync && <button type="button" className="btn btn--secondary btn--sm" onClick={onRetrySync}>Try again</button>}
          <button type="button" className="chat__banner-close" onClick={onDismissSyncNotice} aria-label="Dismiss message">
            <CloseIcon />
          </button>
        </div>
      )}

      <MessageList
        conversation={conversation}
        pending={pending}
        onRetry={assistant.retry}
        canRetry={assistant.canRetry}
        onExample={sendExample}
      />

      <Composer
        busy={!!pending}
        attachment={attachment}
        onAttach={attach}
        onRemoveAttachment={clearAttachment}
        onAnalyze={analyze}
        onSendText={assistant.sendText}
        feedback={feedback}
        onFeedback={setFeedback}
      />

      {dragging && (
        <div className="drop-overlay" aria-hidden="true">
          <UploadIcon />
          <span>Drop a crop photo to analyze</span>
        </div>
      )}
    </section>
  );
}
