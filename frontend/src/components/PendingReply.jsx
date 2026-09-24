const IMAGE_STAGES = {
  uploading: "Uploading image…",
  analyzing: "Analyzing crop…",
  checking: "Checking possible disease…",
};

/** Assistant-side placeholder while a reply is on its way. */
export default function PendingReply({ pending }) {
  const isImage = pending.kind === "image";
  const label = isImage ? IMAGE_STAGES[pending.stage] || IMAGE_STAGES.uploading : "Thinking";

  return (
    <div className="message message--assistant message--enter" role="status" aria-live="polite">
      <div className="bubble bubble--assistant bubble--pending">
        {isImage ? (
          <span className="pending-stage"><span className="spinner" aria-hidden="true" />{label}</span>
        ) : (
          <span className="pending-thinking">
            {label}
            <span className="typing-dots" aria-hidden="true"><span /><span /><span /></span>
          </span>
        )}
      </div>
    </div>
  );
}
