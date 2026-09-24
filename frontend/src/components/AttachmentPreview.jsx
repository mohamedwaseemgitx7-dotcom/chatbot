import { CloseIcon } from "./Icons";
import { formatBytes } from "../utils/format";

/** Selected crop photo, waiting for the user to confirm the analysis. */
export default function AttachmentPreview({ attachment, busy, waitSeconds = 0, onRemove, onAnalyze }) {
  return (
    <div className="attachment" role="group" aria-label="Selected crop photo">
      <img className="attachment__thumb" src={attachment.url} alt="Preview of the selected crop photo" />
      <div className="attachment__info">
        <span className="attachment__name" title={attachment.file.name}>{attachment.file.name}</span>
        <span className="attachment__size">{formatBytes(attachment.file.size)}</span>
      </div>
      <div className="attachment__actions">
        <button type="button" className="btn btn--primary" onClick={onAnalyze} disabled={busy || waitSeconds > 0}>
          {waitSeconds > 0 ? `Analyze in ${waitSeconds} s` : "Analyze photo"}
        </button>
        <button type="button" className="icon-btn" onClick={onRemove} aria-label="Remove photo" title="Remove photo">
          <CloseIcon />
        </button>
      </div>
    </div>
  );
}
