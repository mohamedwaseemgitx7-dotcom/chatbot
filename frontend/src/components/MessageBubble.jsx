import { memo, useEffect, useState } from "react";
import ImageResultCard from "./ImageResultCard";
import { AlertIcon, ImageIcon, RetryIcon } from "./Icons";
import RichText from "./RichText";
import SourceList from "./SourceList";
import { supabaseConfigured } from "../lib/supabase";
import { getImageUrl } from "../services/storageService";
import { formatBytes, formatTime, langTag } from "../utils/format";

/** Photos saved to Storage are private; fetch a short-lived signed URL to show them. */
function useStoredImageUrl(path, localUrl) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    if (localUrl || !path || !supabaseConfigured) return undefined;
    let cancelled = false;
    getImageUrl(path).then((u) => { if (!cancelled) setUrl(u); }).catch(() => {});
    return () => { cancelled = true; };
  }, [path, localUrl]);
  return localUrl || url;
}

function UserImage({ image }) {
  const src = useStoredImageUrl(image?.path, image?.url);
  if (src) {
    return <img className="bubble__photo" src={src} alt={`Crop photo you sent${image.name ? `: ${image.name}` : ""}`} />;
  }
  // No stored copy (or its link is still loading): show the file details instead.
  return (
    <span className="bubble__photo-missing">
      <ImageIcon />
      <span>
        {image?.name || "Crop photo"}
        {image?.size ? <small> · {formatBytes(image.size)}</small> : null}
      </span>
    </span>
  );
}

function MessageBubble({ message, animate, canRetry, onRetry, retryDisabled }) {
  const isUser = message.role === "user";
  const time = new Date(message.createdAt);
  const failed = isUser && message.status === "failed";

  let body;
  if (message.kind === "image") body = <UserImage image={message.image} />;
  else if (message.kind === "image-result") body = <ImageResultCard result={message.result} />;
  else if (isUser) body = <p className="bubble__text" lang={langTag(message.language)}>{message.text}</p>;
  else body = (
    <>
      <RichText text={message.text} lang={langTag(message.language)} />
      <SourceList sources={message.sources} />
    </>
  );

  const classes = [
    "message",
    isUser ? "message--user" : "message--assistant",
    animate && "message--enter",
  ].filter(Boolean).join(" ");

  return (
    <div className={classes}>
      <div
        className={[
          "bubble",
          isUser ? "bubble--user" : "bubble--assistant",
          message.kind === "image" && "bubble--photo",
          message.kind === "image-result" && "bubble--card",
          failed && "bubble--failed",
        ].filter(Boolean).join(" ")}
      >
        <span className="visually-hidden">{isUser ? "You said:" : "FarmerAssist said:"}</span>
        {body}
      </div>

      <div className="message__meta">
        {isUser && message.status === "sending" && <span>Sending…</span>}
        {!(isUser && message.status === "sending") && <time dateTime={time.toISOString()}>{formatTime(time)}</time>}
      </div>

      {failed && (
        <div className="message__error" role="alert">
          <AlertIcon />
          <span>{message.error?.message || "This message wasn't sent. Please try again."}</span>
          {message.error?.retryable !== false && canRetry && (
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => onRetry(message.id)} disabled={retryDisabled}>
              <RetryIcon /> Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(MessageBubble);
