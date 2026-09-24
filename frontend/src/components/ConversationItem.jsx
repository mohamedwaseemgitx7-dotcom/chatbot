import { memo } from "react";
import { TrashIcon } from "./Icons";
import { conditionName, cropName } from "../utils/cropResult";
import { formatListTime } from "../utils/format";

function previewOf(conversation) {
  const last = conversation.messages[conversation.messages.length - 1] || conversation.lastMessage;
  if (!last) return "No messages yet";
  if (last.role === "user" && last.status === "failed") return "Not sent — open to retry";
  const prefix = last.role === "user" ? "You: " : "";
  if (last.kind === "image") return `${prefix}Crop photo`;
  if (last.kind === "image-result") return `Crop analysis · ${cropName(last.result)} · ${conditionName(last.result)}`;
  return prefix + (last.text || "").replace(/\s+/g, " ").trim();
}

function ConversationItem({ conversation, active, onSelect, onDelete }) {
  return (
    <li className={`conversation${active ? " conversation--active" : ""}`}>
      <button
        type="button"
        className="conversation__main"
        onClick={() => onSelect(conversation.id)}
        aria-current={active ? "page" : undefined}
      >
        <span className="conversation__row">
          <span className="conversation__title">{conversation.title}</span>
          <time className="conversation__time" dateTime={new Date(conversation.updatedAt).toISOString()}>
            {formatListTime(new Date(conversation.updatedAt))}
          </time>
        </span>
        <span className="conversation__preview">{previewOf(conversation)}</span>
      </button>
      <button
        type="button"
        className="icon-btn conversation__delete"
        onClick={() => onDelete(conversation)}
        aria-label={`Delete conversation: ${conversation.title}`}
        title="Delete conversation"
      >
        <TrashIcon />
      </button>
    </li>
  );
}

export default memo(ConversationItem);
