import { useState } from "react";
import { CloseIcon, InfoIcon } from "./Icons";

/** Exact wording requested for the WhatsApp-demo notice (used on the login page, banner and About dialog). */
export const DEMO_NOTICE =
  "This is the current demo version of the FarmerAssist WhatsApp chatbot. Live WhatsApp integration is temporarily " +
  "unavailable because the Meta WhatsApp Cloud API demo credits have ended. You are currently using the web demo version.";

const DISMISSED_KEY = "farmerassist.demoNotice.dismissed";

function wasDismissed() {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

/** A calm, dismissible information banner shown once at the top of the chat (not an error, not per message). */
export default function DemoNotice() {
  const [hidden, setHidden] = useState(wasDismissed);
  if (hidden) return null;
  const dismiss = () => {
    setHidden(true);
    try {
      localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // not remembered — shown again next visit
    }
  };
  return (
    <aside className="demo-notice" aria-label="About this demo">
      <InfoIcon />
      <p>{DEMO_NOTICE}</p>
      <button type="button" className="demo-notice__close" onClick={dismiss} aria-label="Dismiss notice">
        <CloseIcon />
      </button>
    </aside>
  );
}
