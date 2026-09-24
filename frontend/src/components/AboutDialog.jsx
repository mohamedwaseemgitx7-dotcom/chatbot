import { useEffect, useRef } from "react";
import { DEMO_NOTICE } from "./DemoNotice";
import "./ConfirmDialog.css";

/** "About FarmerAssist" — native <dialog> (Escape, focus trap and backdrop handled by the browser). */
export default function AboutDialog({ open, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} className="dialog" aria-labelledby="about-title"
            onCancel={(e) => { e.preventDefault(); onClose(); }}
            onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      {open && (
        <div className="dialog__body">
          <h2 id="about-title" className="dialog__title">About FarmerAssist</h2>
          <p className="dialog__message">{DEMO_NOTICE}</p>
          <p className="dialog__message">
            Answers come from the TNAU Agritech Portal (official source, pending expert review) and photo results are
            preliminary AI predictions. Always confirm pesticide or fertilizer decisions with your local agriculture officer.
          </p>
          <div className="dialog__actions">
            <button type="button" className="btn btn--primary" onClick={onClose} autoFocus>Close</button>
          </div>
        </div>
      )}
    </dialog>
  );
}
