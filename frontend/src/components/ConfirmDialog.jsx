import { useEffect, useRef } from "react";
import "./ConfirmDialog.css";

/** Native <dialog>: the browser handles focus trapping, Escape and the backdrop. */
export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", busy = false, error = null, onConfirm, onCancel }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby="dialog-title"
      aria-describedby="dialog-message"
      onCancel={(e) => { e.preventDefault(); onCancel(); }}
      onClick={(e) => { if (e.target === ref.current) onCancel(); }}
    >
      {open && (
        <form className="dialog__body" onSubmit={(e) => { e.preventDefault(); onConfirm(); }}>
          <h2 id="dialog-title" className="dialog__title">{title}</h2>
          <p id="dialog-message" className="dialog__message">{message}</p>
          {error && <p className="dialog__error" role="alert">{error}</p>}
          <div className="dialog__actions">
            <button type="button" className="btn btn--secondary" onClick={onCancel} disabled={busy} autoFocus>Cancel</button>
            <button type="submit" className="btn btn--danger" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              {busy ? "Deleting…" : confirmLabel}
            </button>
          </div>
        </form>
      )}
    </dialog>
  );
}
